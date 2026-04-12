"""
High-level data extraction layer for the IG Markets REST API.

Fetches paginated transaction history, activity history, open positions,
working orders, and account details, returning everything as pandas
DataFrames or plain dicts.

IG API endpoints used
---------------------
GET /accounts            v1  – list of accounts with balance info
GET /history/transactions  v2  – closed trade P&L (paginated)
GET /history/activity    v3  – trade/order events (paginated)
GET /positions           v2  – open positions
GET /workingorders       v2  – pending orders
"""

import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ig_client import IGClient

logger = logging.getLogger(__name__)

# IG /history/transactions returns up to 500 records per page
_TX_PAGE_SIZE = 500
# IG /history/activity returns up to 500 records per page
_ACT_PAGE_SIZE = 500


def _parse_pnl(value: Any) -> float:
    """
    Parse an IG profitAndLoss string into a plain float.

    IG can return values like:
      "1234.56", "-567.89", "£1,234.56", "-£567.89",
      "0.00", "USD 1234.56", "1,234.56"
    """
    if value is None:
        return 0.0
    text = str(value).strip()
    # Remove currency symbols, letters and thousands separators
    text = re.sub(r"[£$€¥₹A-Za-z,\s]", "", text)
    try:
        return float(text)
    except ValueError:
        return 0.0


def _to_datetime(value: Any) -> Optional[datetime]:
    """Try a variety of ISO-8601 formats used by IG."""
    if not value:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(value)[:26], fmt)
        except ValueError:
            continue
    logger.debug("Could not parse date: %r", value)
    return None


class DataExtractor:
    """Fetches all trading data from the IG API for a given date range."""

    def __init__(self, client: IGClient) -> None:
        self._c = client

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Return list of all accounts with balance and margin info."""
        body = self._c.get("/accounts", version=1)
        accounts = body.get("accounts", [])
        logger.info("Found %d account(s).", len(accounts))
        return accounts

    # ------------------------------------------------------------------
    # Transactions (closed trades – the main P&L source)
    # ------------------------------------------------------------------

    def get_transactions(
        self,
        from_date: str,
        to_date: str,
        tx_type: str = "ALL",
    ) -> pd.DataFrame:
        """
        Fetch all closed-trade transactions between *from_date* and *to_date*.

        Parameters
        ----------
        from_date : str  e.g. "2024-01-01"
        to_date   : str  e.g. "2025-12-31"
        tx_type   : "ALL" | "DEAL" | "DEPO" | "WITH"

        Returns
        -------
        pd.DataFrame with one row per transaction, columns:
            date_utc, instrument, direction, size, open_level, close_level,
            pnl, currency, reference, period, transaction_type
        """
        from_iso = f"{from_date}T00:00:00"
        to_iso = f"{to_date}T23:59:59"

        all_rows: List[Dict[str, Any]] = []
        page = 1

        logger.info(
            "Fetching transactions [%s → %s, type=%s] …", from_date, to_date, tx_type
        )

        while True:
            params = {
                "type": tx_type,
                "from": from_iso,
                "to": to_iso,
                "pageSize": _TX_PAGE_SIZE,
                "pageNumber": page,
            }
            body = self._c.get("/history/transactions", version=2, params=params)
            rows = body.get("transactions", [])
            all_rows.extend(rows)

            meta = body.get("metadata", {}).get("pageData", {})
            total = int(meta.get("totalCount", len(rows)))
            logger.debug(
                "  Page %d: got %d rows (total so far: %d / %d)",
                page,
                len(rows),
                len(all_rows),
                total,
            )

            if len(all_rows) >= total or not rows:
                break
            page += 1
            time.sleep(0.25)  # be polite to the rate limiter

        logger.info("Total transactions fetched: %d", len(all_rows))

        if not all_rows:
            return pd.DataFrame()

        records = []
        for tx in all_rows:
            close_dt = _to_datetime(tx.get("date") or tx.get("closeDate"))
            open_dt = _to_datetime(tx.get("openDate"))

            pnl_raw = tx.get("profitAndLoss", "0")
            pnl = _parse_pnl(pnl_raw)

            size_raw = tx.get("size", "0")
            try:
                size = float(str(size_raw).replace(",", ""))
            except ValueError:
                size = 0.0

            try:
                open_level = float(tx.get("openLevel") or 0)
            except (TypeError, ValueError):
                open_level = 0.0

            try:
                close_level = float(tx.get("closeLevel") or 0)
            except (TypeError, ValueError):
                close_level = 0.0

            # Infer direction from size sign or openLevel vs closeLevel
            direction = tx.get("tradeSize", "")
            if not direction:
                if size < 0:
                    direction = "SELL"
                else:
                    direction = "BUY"

            records.append(
                {
                    "close_date": close_dt,
                    "open_date": open_dt,
                    "instrument": tx.get("instrumentName", ""),
                    "direction": direction,
                    "size": abs(size),
                    "open_level": open_level,
                    "close_level": close_level,
                    "pnl": pnl,
                    "currency": tx.get("currency", ""),
                    "reference": tx.get("reference", ""),
                    "period": tx.get("period", ""),
                    "transaction_type": tx.get("transactionType", ""),
                }
            )

        df = pd.DataFrame(records)
        df.sort_values("close_date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    # ------------------------------------------------------------------
    # Activity history (trade events)
    # ------------------------------------------------------------------

    def get_activity(
        self,
        from_date: str,
        to_date: str,
    ) -> pd.DataFrame:
        """
        Fetch activity history (position opened/closed, orders, etc.).

        Returns a DataFrame with deal-level detail including stop/limit levels,
        deal references, and actions performed.
        """
        from_iso = f"{from_date}T00:00:00"
        to_iso = f"{to_date}T23:59:59"

        all_rows: List[Dict[str, Any]] = []
        page = 1

        logger.info("Fetching activity history [%s → %s] …", from_date, to_date)

        while True:
            params = {
                "from": from_iso,
                "to": to_iso,
                "detailed": "true",
                "pageSize": _ACT_PAGE_SIZE,
                "pageNumber": page,
            }
            body = self._c.get("/history/activity", version=3, params=params)
            rows = body.get("activities", [])
            all_rows.extend(rows)

            meta = body.get("metadata", {}).get("pageData", {})
            total = int(meta.get("totalCount", len(rows)))
            logger.debug(
                "  Activity page %d: got %d rows (%d / %d)",
                page,
                len(rows),
                len(all_rows),
                total,
            )

            if len(all_rows) >= total or not rows:
                break
            page += 1
            time.sleep(0.25)

        logger.info("Total activity records fetched: %d", len(all_rows))

        if not all_rows:
            return pd.DataFrame()

        records = []
        for act in all_rows:
            dt = _to_datetime(act.get("date"))
            details = act.get("details", {}) or {}
            records.append(
                {
                    "date": dt,
                    "epic": act.get("epic", ""),
                    "instrument": act.get("instrumentName", ""),
                    "action": act.get("action", ""),
                    "deal_id": act.get("dealId", ""),
                    "deal_reference": act.get("dealReference", ""),
                    "direction": details.get("direction", ""),
                    "size": details.get("size", 0),
                    "level": details.get("level", 0),
                    "stop_level": details.get("stopLevel"),
                    "limit_level": details.get("limitLevel"),
                    "currency": details.get("currency", ""),
                    "status": act.get("status", ""),
                }
            )

        df = pd.DataFrame(records)
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    # ------------------------------------------------------------------
    # Open positions
    # ------------------------------------------------------------------

    def get_open_positions(self) -> pd.DataFrame:
        """Return current open positions as a DataFrame."""
        body = self._c.get("/positions", version=2)
        positions = body.get("positions", [])
        logger.info("Open positions: %d", len(positions))

        if not positions:
            return pd.DataFrame()

        records = []
        for pos in positions:
            p = pos.get("position", {})
            mkt = pos.get("market", {})
            records.append(
                {
                    "deal_id": p.get("dealId", ""),
                    "instrument": mkt.get("instrumentName", ""),
                    "epic": mkt.get("epic", ""),
                    "direction": p.get("direction", ""),
                    "size": p.get("size", 0),
                    "open_level": p.get("level", 0),
                    "current_bid": mkt.get("bid", 0),
                    "current_offer": mkt.get("offer", 0),
                    "currency": p.get("currency", ""),
                    "created_date": _to_datetime(p.get("createdDateUTC")),
                    "stop_level": p.get("stopLevel"),
                    "limit_level": p.get("limitLevel"),
                    "unrealised_pnl": p.get("upl", 0),
                }
            )

        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # Working orders
    # ------------------------------------------------------------------

    def get_working_orders(self) -> pd.DataFrame:
        """Return pending (working) orders as a DataFrame."""
        body = self._c.get("/workingorders", version=2)
        orders = body.get("workingOrders", [])
        logger.info("Working orders: %d", len(orders))

        if not orders:
            return pd.DataFrame()

        records = []
        for wo in orders:
            wd = wo.get("workingOrderData", {})
            mkt = wo.get("marketData", {})
            records.append(
                {
                    "deal_id": wd.get("dealId", ""),
                    "instrument": mkt.get("instrumentName", ""),
                    "epic": mkt.get("epic", ""),
                    "direction": wd.get("direction", ""),
                    "size": wd.get("orderSize", 0),
                    "order_level": wd.get("orderLevel", 0),
                    "order_type": wd.get("orderType", ""),
                    "currency": wd.get("currencyCode", ""),
                    "created_date": _to_datetime(wd.get("createdDateUTC")),
                    "good_till_date": _to_datetime(wd.get("goodTillDate")),
                    "stop_distance": wd.get("stopDistance"),
                    "limit_distance": wd.get("limitDistance"),
                }
            )

        return pd.DataFrame(records)
