"""
Low-level IG Markets REST API client.

Handles authentication (session creation/deletion), request signing with
CST + X-SECURITY-TOKEN headers, automatic retries on transient errors, and
versioned endpoint calls.

IG REST API base docs: https://labs.ig.com/rest-trading-api-reference
"""

import time
import logging
from typing import Any, Dict, Optional

import requests

import config

logger = logging.getLogger(__name__)


class IGAPIError(Exception):
    """Raised when the IG API returns a non-2xx response."""

    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(f"[{status_code}] {error_code}: {message}")


class IGClient:
    """
    Authenticated HTTP client for the IG REST API.

    Usage::

        client = IGClient()
        client.login()
        data = client.get("/accounts", version=1)
        client.logout()

    Or use as a context manager::

        with IGClient() as client:
            data = client.get("/accounts", version=1)
    """

    _RETRY_STATUSES = {429, 500, 502, 503, 504}
    _MAX_RETRIES = 4
    _BACKOFF_BASE = 2  # seconds

    def __init__(
        self,
        api_key: str = config.IG_API_KEY,
        username: str = config.IG_USERNAME,
        password: str = config.IG_PASSWORD,
        base_url: str = config.BASE_URL,
        account_id: str = config.IG_ACCOUNT_ID,
    ) -> None:
        if not api_key:
            raise ValueError("IG_API_KEY is not set. Check your .env file.")
        if not username:
            raise ValueError("IG_USERNAME is not set. Check your .env file.")
        if not password:
            raise ValueError("IG_PASSWORD is not set. Check your .env file.")

        self._api_key = api_key
        self._username = username
        self._password = password
        self._base_url = base_url.rstrip("/")
        self._preferred_account_id = account_id

        self._session = requests.Session()
        self._cst: Optional[str] = None
        self._security_token: Optional[str] = None
        self._account_id: Optional[str] = None
        self._logged_in = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def login(self) -> Dict[str, Any]:
        """
        Create an IG session (v1 – plain-text password over TLS).

        Returns the full session response body which includes account list,
        currency, timezone offset etc.
        """
        payload = {
            "identifier": self._username,
            "password": self._password,
        }
        headers = self._base_headers(version=1)
        url = f"{self._base_url}/session"

        logger.info("Logging in to IG as %s …", self._username)
        resp = self._session.post(url, json=payload, headers=headers, timeout=30)
        self._raise_for_status(resp)

        self._cst = resp.headers.get("CST")
        self._security_token = resp.headers.get("X-SECURITY-TOKEN")
        self._logged_in = True

        body = resp.json()

        # Determine which account to use
        accounts = body.get("accounts", [])
        if self._preferred_account_id:
            self._account_id = self._preferred_account_id
        elif accounts:
            self._account_id = accounts[0].get("accountId")
        else:
            self._account_id = body.get("currentAccountId")

        logger.info(
            "Login successful. Account: %s | Timezone offset: %s",
            self._account_id,
            body.get("timezoneOffset"),
        )
        return body

    def logout(self) -> None:
        """Delete the current IG session."""
        if not self._logged_in:
            return
        try:
            self._request("DELETE", "/session", version=1)
            logger.info("Logged out successfully.")
        except Exception as exc:  # pragma: no cover
            logger.warning("Logout failed (non-fatal): %s", exc)
        finally:
            self._logged_in = False
            self._cst = None
            self._security_token = None

    def get(
        self,
        endpoint: str,
        version: int = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Issue an authenticated GET request and return the parsed JSON body."""
        return self._request("GET", endpoint, version=version, params=params)

    def post(
        self,
        endpoint: str,
        version: int = 1,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Issue an authenticated POST request and return the parsed JSON body."""
        return self._request("POST", endpoint, version=version, json=data)

    def put(
        self,
        endpoint: str,
        version: int = 1,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Issue an authenticated PUT request and return the parsed JSON body."""
        return self._request("PUT", endpoint, version=version, json=data)

    def delete(
        self,
        endpoint: str,
        version: int = 1,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Issue an authenticated DELETE request.

        IG uses a POST with _method=DELETE header for position closes
        (some endpoints require this pattern).
        """
        # IG position close requires POST with _method override header
        headers = self._base_headers(version)
        headers["_method"] = "DELETE"
        url = f"{self._base_url}{endpoint}"
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                resp = self._session.post(
                    url, headers=headers, json=data, timeout=30
                )
            except requests.RequestException as exc:
                if attempt == self._MAX_RETRIES:
                    raise
                time.sleep(self._BACKOFF_BASE ** attempt)
                continue
            self._raise_for_status(resp)
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()
        raise RuntimeError("Exceeded maximum retries")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "IGClient":
        self.login()
        return self

    def __exit__(self, *_: Any) -> None:
        self.logout()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_headers(self, version: int) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json; charset=UTF-8",
            "X-IG-API-KEY": self._api_key,
            "Version": str(version),
        }
        if self._cst:
            headers["CST"] = self._cst
        if self._security_token:
            headers["X-SECURITY-TOKEN"] = self._security_token
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        version: int = 1,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self._base_url}{endpoint}"
        headers = self._base_headers(version)

        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                resp = self._session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=30,
                )
            except requests.RequestException as exc:
                if attempt == self._MAX_RETRIES:
                    raise
                wait = self._BACKOFF_BASE ** attempt
                logger.warning(
                    "Network error on attempt %d/%d: %s – retrying in %ds",
                    attempt,
                    self._MAX_RETRIES,
                    exc,
                    wait,
                )
                time.sleep(wait)
                continue

            if resp.status_code in self._RETRY_STATUSES and attempt < self._MAX_RETRIES:
                wait = self._BACKOFF_BASE ** attempt
                logger.warning(
                    "HTTP %d on attempt %d/%d – retrying in %ds",
                    resp.status_code,
                    attempt,
                    self._MAX_RETRIES,
                    wait,
                )
                time.sleep(wait)
                continue

            self._raise_for_status(resp)

            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()

        raise RuntimeError("Exceeded maximum retries")  # pragma: no cover

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        if resp.ok:
            return
        try:
            body = resp.json()
            error_code = body.get("errorCode", "UNKNOWN")
            message = body.get("errorDetails", str(body))
        except Exception:
            error_code = "PARSE_ERROR"
            message = resp.text[:500]
        raise IGAPIError(resp.status_code, error_code, message)
