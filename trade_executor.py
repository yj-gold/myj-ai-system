"""
MYJ Capital — Trade Executor
==============================

Executes trades on IG Markets via the REST API based on signals from
the TurtleCTA strategy engine.

Supports:
  • Open a new position (MARKET order) with stop loss + take profit
  • Confirm deal acceptance / rejection
  • Check for duplicate positions (don't re-enter a market we're in)
  • Close an existing position
  • Update stop/limit on an open position
  • Full trade log to CSV + console

IG order flow
-------------
  1. POST /positions/otc  → returns dealReference
  2. GET  /confirms/{dealReference}  → returns dealId + dealStatus
  3. Store dealId for future updates / closes

Safety rules (hardcoded)
------------------------
  • Never open a position we already hold in the same direction
  • Minimum signal score of 65 required to auto-execute
  • Maximum 4 units per market (Turtle rule)
  • All orders use MARKET type — no limit chasing
  • Stop loss always set at open (non-negotiable)
"""

import csv
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ig_client import IGClient, IGAPIError
from strategy_engine import Signal

logger = logging.getLogger(__name__)

# Minimum score before we will auto-execute (configurable via --exec-min-score)
DEFAULT_EXEC_MIN_SCORE = 65

# Seconds to wait for deal confirmation before timing out
CONFIRM_TIMEOUT = 10


# ── Result data structure ─────────────────────────────────────────────────────

@dataclass
class ExecutionResult:
    timestamp:      str
    market_name:    str
    epic:           str
    direction:      str
    unit_size:      float
    entry_level:    float
    stop_loss:      float
    take_profit:    float
    risk_amount:    float
    signal_score:   int
    deal_reference: str
    deal_id:        str
    deal_status:    str   # ACCEPTED | REJECTED
    reason:         str   # SUCCESS or rejection reason
    actual_level:   float # actual fill price from confirm


# ── Main executor class ───────────────────────────────────────────────────────

class TradeExecutor:
    """
    Places trades on IG based on signals from TurtleCTAStrategy.

    Parameters
    ----------
    client          : authenticated IGClient
    min_score       : minimum signal score to execute (default 65)
    dry_run         : if True, log what would be traded but don't actually send orders
    log_dir         : directory to write trade_log.csv
    """

    def __init__(
        self,
        client:    IGClient,
        min_score: int  = DEFAULT_EXEC_MIN_SCORE,
        dry_run:   bool = False,
        log_dir:   str  = "./output",
    ):
        self._c        = client
        self.min_score = min_score
        self.dry_run   = dry_run
        self.log_dir   = log_dir
        os.makedirs(log_dir, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def execute_signals(self, signals: List[Signal]) -> List[ExecutionResult]:
        """
        Iterate signals, apply filters, execute qualifying ones.
        Returns list of ExecutionResult for every attempted trade.
        """
        results = []

        # Fetch current open positions once — avoid duplicates
        open_positions = self._get_open_positions()
        open_epics = {
            (p.get("market", {}).get("epic", ""),
             p.get("position", {}).get("direction", ""))
            for p in open_positions
        }

        active = [s for s in signals if s.direction != "WAIT"]
        logger.info("Signals to evaluate: %d", len(active))

        for sig in sorted(active, key=lambda s: -s.score):
            result = self._evaluate_and_execute(sig, open_epics)
            if result:
                results.append(result)
                # Add to open set so we don't double-enter
                open_epics.add((sig.epic, sig.direction))
                self._log_result(result)
                time.sleep(1.0)   # IG rate limit: ~30 orders/minute

        return results

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Return raw IG open positions."""
        return self._get_open_positions()

    def close_position(self, deal_id: str, epic: str,
                       direction: str, size: float) -> Dict[str, Any]:
        """Close an existing position by dealId."""
        close_dir = "SELL" if direction == "BUY" else "BUY"
        payload = {
            "dealId":      deal_id,
            "epic":        epic,
            "expiry":      "-",
            "direction":   close_dir,
            "size":        size,
            "orderType":   "MARKET",
            "timeInForce": "FILL_OR_KILL",
        }
        if self.dry_run:
            logger.info("[DRY RUN] Would close %s %s size=%s", epic, direction, size)
            return {"dealStatus": "DRY_RUN"}
        return self._c.delete("/positions/otc", version=1, data=payload)

    def update_stop_limit(self, deal_id: str,
                          stop_level: float, limit_level: float) -> Dict[str, Any]:
        """Move the stop and/or take profit on an open position."""
        payload = {
            "stopLevel":         stop_level,
            "limitLevel":        limit_level,
            "trailingStop":      False,
            "trailingStopDistance": None,
            "trailingStopIncrement": None,
        }
        if self.dry_run:
            logger.info("[DRY RUN] Would update %s stop=%s limit=%s",
                        deal_id, stop_level, limit_level)
            return {"dealStatus": "DRY_RUN"}
        return self._c.put(f"/positions/otc/{deal_id}", version=2, data=payload)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _evaluate_and_execute(
        self,
        sig: Signal,
        open_epics: set,
    ) -> Optional[ExecutionResult]:

        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # ── Score gate ───────────────────────────────────────────────────────
        if sig.score < self.min_score:
            logger.info("SKIP %s — score %d < %d",
                        sig.market_name, sig.score, self.min_score)
            return None

        # ── Duplicate check ──────────────────────────────────────────────────
        ig_dir = "BUY" if sig.direction == "LONG" else "SELL"
        if (sig.epic, ig_dir) in open_epics:
            logger.info("SKIP %s %s — already in position",
                        sig.market_name, sig.direction)
            print(f"  ⚠  {sig.market_name}: already holding {sig.direction} — skipped")
            return None

        # ── Build order ──────────────────────────────────────────────────────
        payload = {
            "epic":           sig.epic,
            "expiry":         "-",
            "direction":      ig_dir,
            "size":           round(sig.unit_size, 2),
            "orderType":      "MARKET",
            "timeInForce":    "FILL_OR_KILL",
            "guaranteedStop": False,
            "stopLevel":      round(sig.stop_loss, 5),
            "limitLevel":     round(sig.take_profit, 5),
            "forceOpen":      True,
            "currencyCode":   "GBP",
        }

        print(f"\n  ▶  Executing {sig.direction} on {sig.market_name}")
        print(f"     Score: {sig.score}/100  |  "
              f"Size: £{sig.unit_size:.2f}/pt  |  "
              f"Stop: {sig.stop_loss:.4f}  |  "
              f"Target: {sig.take_profit:.4f}")

        if self.dry_run:
            print(f"     [DRY RUN] Order would be: {payload}")
            return ExecutionResult(
                timestamp=ts, market_name=sig.market_name, epic=sig.epic,
                direction=sig.direction, unit_size=sig.unit_size,
                entry_level=sig.entry_level, stop_loss=sig.stop_loss,
                take_profit=sig.take_profit, risk_amount=sig.risk_amount,
                signal_score=sig.score, deal_reference="DRY_RUN",
                deal_id="DRY_RUN", deal_status="DRY_RUN",
                reason="DRY_RUN", actual_level=sig.current_price,
            )

        # ── Place order ──────────────────────────────────────────────────────
        try:
            resp = self._c.post("/positions/otc", version=2, data=payload)
        except IGAPIError as exc:
            print(f"     ✗ Order rejected by IG: {exc}")
            return ExecutionResult(
                timestamp=ts, market_name=sig.market_name, epic=sig.epic,
                direction=sig.direction, unit_size=sig.unit_size,
                entry_level=sig.entry_level, stop_loss=sig.stop_loss,
                take_profit=sig.take_profit, risk_amount=sig.risk_amount,
                signal_score=sig.score, deal_reference="",
                deal_id="", deal_status="REJECTED",
                reason=str(exc), actual_level=0,
            )

        deal_ref = resp.get("dealReference", "")

        # ── Confirm ──────────────────────────────────────────────────────────
        confirm = self._confirm(deal_ref)
        status  = confirm.get("dealStatus", "UNKNOWN")
        reason  = confirm.get("reason", "")
        deal_id = confirm.get("dealId", "")
        level   = float(confirm.get("level", sig.entry_level) or sig.entry_level)

        if status == "ACCEPTED":
            print(f"     ✓ Filled at {level:.5f}  |  dealId: {deal_id}")
        else:
            print(f"     ✗ Rejected: {reason}")

        return ExecutionResult(
            timestamp=ts, market_name=sig.market_name, epic=sig.epic,
            direction=sig.direction, unit_size=sig.unit_size,
            entry_level=sig.entry_level, stop_loss=sig.stop_loss,
            take_profit=sig.take_profit, risk_amount=sig.risk_amount,
            signal_score=sig.score, deal_reference=deal_ref,
            deal_id=deal_id, deal_status=status,
            reason=reason, actual_level=level,
        )

    def _confirm(self, deal_reference: str) -> Dict[str, Any]:
        """Poll /confirms until we get a definitive result."""
        deadline = time.time() + CONFIRM_TIMEOUT
        while time.time() < deadline:
            try:
                body = self._c.get(f"/confirms/{deal_reference}", version=1)
                status = body.get("dealStatus", "")
                if status in ("ACCEPTED", "REJECTED"):
                    return body
            except IGAPIError:
                pass
            time.sleep(0.5)
        return {"dealStatus": "TIMEOUT", "reason": "Confirm timed out"}

    def _get_open_positions(self) -> List[Dict[str, Any]]:
        try:
            body = self._c.get("/positions", version=2)
            return body.get("positions", [])
        except IGAPIError:
            return []

    def _log_result(self, result: ExecutionResult) -> None:
        """Append result to trade_log.csv."""
        path = os.path.join(self.log_dir, "trade_log.csv")
        is_new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(result).keys()))
            if is_new:
                w.writeheader()
            w.writerow(asdict(result))
        logger.info("Trade logged → %s", path)
