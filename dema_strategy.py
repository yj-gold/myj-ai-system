"""
MYJ Capital — DEMA28 Multi-Timeframe Strategy
==============================================

Generates LONG/SHORT signals when price is on the same side of the
Double Exponential Moving Average (period 28) on ALL five timeframes
simultaneously:

  3-minute  · 5-minute  · 15-minute  · 4-hour  · Daily

  LONG  when price > DEMA28 on all 5 timeframes
  SHORT when price < DEMA28 on all 5 timeframes
  WAIT  when any timeframe disagrees

DEMA formula:
  EMA1 = EMA(price, 28)
  EMA2 = EMA(EMA1,  28)
  DEMA = 2 × EMA1 − EMA2

DEMA reacts faster than a plain EMA but is smoother than a raw price
series — ideal for crossover confirmation across multiple timeframes.

Position sizing:
  Same Turtle formula as TurtleCTAStrategy:
  Risk £ = equity × risk_pct
  Stop   = 2 × daily ATR(20)
  Target = 4 × daily ATR(20)  →  2 : 1 reward : risk
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging
import math
import time

from strategy_engine import OHLC, _ema, _atr
from ig_client import IGAPIError

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DEMA_PERIOD = 28

# (IG resolution string, bars to request, calendar days to look back)
TIMEFRAMES: Dict[str, Tuple[str, int, int]] = {
    "3min":  ("MINUTE_3",  90, 1),
    "5min":  ("MINUTE_5",  90, 2),
    "15min": ("MINUTE_15", 90, 4),
    "4h":    ("HOUR_4",    60, 15),
    "daily": ("DAY",       60, 90),
}


# ── DEMA indicator ────────────────────────────────────────────────────────────

def _dema(prices: List[float], period: int = DEMA_PERIOD) -> List[float]:
    """
    Double Exponential Moving Average.
    Returns same-length list (leading values are NaN until indicator is warm).
    """
    ema1 = _ema(prices, period)

    # Find where EMA1 first becomes valid
    valid_start = next((i for i, v in enumerate(ema1) if not math.isnan(v)), None)
    if valid_start is None:
        return [float("nan")] * len(prices)

    # Second EMA pass on the valid portion of EMA1
    ema2_raw = _ema(ema1[valid_start:], period)
    ema2 = [float("nan")] * valid_start + ema2_raw

    result = []
    for e1, e2 in zip(ema1, ema2):
        if math.isnan(e1) or math.isnan(e2):
            result.append(float("nan"))
        else:
            result.append(2.0 * e1 - e2)
    return result


# ── Signal dataclass (mirrors Signal for duck-typing with send_alert) ─────────

@dataclass
class DEMASignal:
    """
    Output of DEMAMultiTimeframeStrategy.

    Fields intentionally mirror strategy_engine.Signal so the same
    email/display code works without modification.
    """
    market_name:    str
    epic:           str
    direction:      str           # LONG | SHORT | WAIT
    system:         int           # always DEMA_PERIOD (28)
    score:          int           # 20 × number of aligned timeframes (max 100)
    current_price:  float
    atr:            float         # daily ATR(20)
    entry_level:    float
    stop_loss:      float
    take_profit:    float
    trail_exit:     float         # same as stop_loss (no channel trail for DEMA)
    unit_size:      float
    risk_amount:    float
    pyramid_levels: List[float]   # empty — no pyramid for DEMA
    ema_21:         float         # daily DEMA28 value (reused field)
    ema_55:         float         # unused
    ema_200:        float         # unused
    adx:            float         # unused
    momentum_12m:   float         # unused
    momentum_3m:    float         # unused
    donchian_20_hi: float         # unused
    donchian_20_lo: float         # unused
    donchian_55_hi: float         # unused
    donchian_55_lo: float         # unused
    reason:         str
    tf_aligned:     Dict[str, bool] = field(default_factory=dict)


# ── Strategy class ────────────────────────────────────────────────────────────

class DEMAMultiTimeframeStrategy:
    """
    DEMA28 multi-timeframe crossover strategy.

    Requires all five timeframes (3min, 5min, 15min, 4h, daily) to
    simultaneously show price on the same side of DEMA28.
    """

    def __init__(
        self,
        account_equity: float,
        risk_pct:   float = 0.01,
        atr_stop:   float = 2.0,
        atr_target: float = 4.0,
    ):
        self.equity     = account_equity
        self.risk_pct   = risk_pct
        self.atr_stop   = atr_stop
        self.atr_target = atr_target

    # ── Public API ────────────────────────────────────────────────────────────

    def analyse(self, client: Any, market: dict) -> DEMASignal:
        """
        Fetch all 5 timeframes, compute DEMA28 on each, check alignment.
        Returns a DEMASignal with direction LONG/SHORT/WAIT.
        """
        epic = market["epic"]
        tf_directions: Dict[str, str] = {}
        tf_dema_vals:  Dict[str, float] = {}
        daily_bars:    List[OHLC] = []

        for tf_name, (resolution, n_bars, days_back) in TIMEFRAMES.items():
            bars = self._fetch_ohlc_tf(client, epic, resolution, n_bars, days_back)
            if tf_name == "daily":
                daily_bars = bars

            if len(bars) < DEMA_PERIOD * 2:
                tf_directions[tf_name] = "WAIT"
                tf_dema_vals[tf_name]  = 0.0
                logger.debug("%s %s: only %d bars — WAIT", market["name"], tf_name, len(bars))
            else:
                direction, dema_val = self._check_alignment(bars)
                tf_directions[tf_name] = direction
                tf_dema_vals[tf_name]  = dema_val

            time.sleep(0.25)   # IG rate limit

        return self._build_signal(market, tf_directions, tf_dema_vals, daily_bars)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_ohlc_tf(
        self,
        client: Any,
        epic:   str,
        resolution: str,
        n_bars: int,
        days_back: int,
    ) -> List[OHLC]:
        to_dt   = datetime.utcnow()
        from_dt = to_dt - timedelta(days=days_back)
        params  = {
            "resolution": resolution,
            "from":       from_dt.strftime("%Y-%m-%dT00:00:00"),
            "to":         to_dt.strftime("%Y-%m-%dT23:59:59"),
            "max":        n_bars,
        }
        try:
            body = client.get(f"/prices/{epic}", version=3, params=params)
        except IGAPIError as exc:
            logger.warning("DEMA: failed %s %s: %s", epic, resolution, exc)
            return []

        bars = []
        for p in body.get("prices", []):
            c = self._mid(p.get("closePrice", {}))
            if c == 0:
                continue
            bars.append(OHLC(
                date   = p.get("snapshotTime", ""),
                open   = self._mid(p.get("openPrice", {})),
                high   = self._mid(p.get("highPrice", {})),
                low    = self._mid(p.get("lowPrice", {})),
                close  = c,
                volume = float(p.get("lastTradedVolume", 0) or 0),
            ))
        return bars

    @staticmethod
    def _mid(d: dict) -> float:
        if d.get("mid") is not None:
            return float(d["mid"])
        bid, ask = d.get("bid"), d.get("ask")
        if bid is not None and ask is not None:
            return (float(bid) + float(ask)) / 2.0
        return float(bid or ask or 0)

    def _check_alignment(self, bars: List[OHLC]) -> Tuple[str, float]:
        """
        Compute DEMA28 on the bar series and check whether the last close
        is above or below DEMA28.

        Returns (direction, dema28_last_value).
        """
        closes = [b.close for b in bars]
        dema   = _dema(closes, DEMA_PERIOD)
        last   = dema[-1]

        if math.isnan(last):
            return "WAIT", 0.0

        price = closes[-1]
        if price > last:
            return "LONG", last
        if price < last:
            return "SHORT", last
        return "WAIT", last

    def _build_signal(
        self,
        market:         dict,
        tf_directions:  Dict[str, str],
        tf_dema_vals:   Dict[str, float],
        daily_bars:     List[OHLC],
    ) -> DEMASignal:
        """Combine timeframe results into a single DEMASignal."""

        all_tfs     = list(TIMEFRAMES.keys())
        directions  = [tf_directions.get(tf, "WAIT") for tf in all_tfs]

        all_long    = all(d == "LONG"  for d in directions)
        all_short   = all(d == "SHORT" for d in directions)

        # Score: 20 per timeframe aligned in the winning direction
        if all_long or all_short:
            target_dir = "LONG" if all_long else "SHORT"
            score      = sum(20 for d in directions if d == target_dir)
        else:
            target_dir = None
            score      = 0

        # Current price and ATR from daily bars
        price  = daily_bars[-1].close if daily_bars else 0.0
        atr_s  = _atr(daily_bars, 20) if len(daily_bars) >= 20 else []
        atr    = atr_s[-1] if atr_s and not math.isnan(atr_s[-1]) else 0.0
        daily_dema = tf_dema_vals.get("daily", 0.0)

        tf_aligned = {tf: tf_directions.get(tf, "WAIT") == target_dir
                      for tf in all_tfs} if target_dir else {tf: False for tf in all_tfs}

        # Timeframe alignment summary
        def _tf_icon(tf: str) -> str:
            d = tf_directions.get(tf, "WAIT")
            ok = (d == target_dir) if target_dir else False
            return f"{tf}:{'✓' if ok else '✗'}"

        reason = " | ".join(_tf_icon(tf) for tf in all_tfs)

        if not (all_long or all_short) or atr == 0 or price == 0:
            tf_count = sum(1 for d in directions if d != "WAIT")
            wait_reason = (
                f"Timeframes aligned: {tf_count}/5 — "
                f"{' | '.join(_tf_icon(tf) for tf in all_tfs)}"
            )
            return self._no_signal(market, price, daily_dema, atr, wait_reason)

        # Entry, stop, target
        direction  = "LONG" if all_long else "SHORT"
        entry      = price
        if direction == "LONG":
            stop   = entry - self.atr_stop   * atr
            target = entry + self.atr_target * atr
        else:
            stop   = entry + self.atr_stop   * atr
            target = entry - self.atr_target * atr

        # Position sizing
        risk_amount   = self.equity * self.risk_pct
        stop_distance = abs(entry - stop)
        unit_size     = risk_amount / stop_distance if stop_distance > 0 else market["min_size"]
        unit_size     = max(unit_size, market["min_size"])

        return DEMASignal(
            market_name    = market["name"],
            epic           = market["epic"],
            direction      = direction,
            system         = DEMA_PERIOD,
            score          = score,
            current_price  = round(price, 5),
            atr            = round(atr, 5),
            entry_level    = round(entry, 5),
            stop_loss      = round(stop, 5),
            take_profit    = round(target, 5),
            trail_exit     = round(stop, 5),
            unit_size      = round(unit_size, 2),
            risk_amount    = round(risk_amount, 2),
            pyramid_levels = [],
            ema_21         = round(daily_dema, 5),
            ema_55         = 0.0,
            ema_200        = 0.0,
            adx            = 0.0,
            momentum_12m   = 0.0,
            momentum_3m    = 0.0,
            donchian_20_hi = 0.0,
            donchian_20_lo = 0.0,
            donchian_55_hi = 0.0,
            donchian_55_lo = 0.0,
            reason         = f"DEMA28 all-TF aligned → {reason}",
            tf_aligned     = tf_aligned,
        )

    def _no_signal(
        self,
        market:     dict,
        price:      float,
        daily_dema: float,
        atr:        float,
        reason:     str,
    ) -> DEMASignal:
        return DEMASignal(
            market_name    = market["name"],
            epic           = market["epic"],
            direction      = "WAIT",
            system         = DEMA_PERIOD,
            score          = 0,
            current_price  = round(price, 5),
            atr            = round(atr, 5),
            entry_level    = price,
            stop_loss      = 0.0,
            take_profit    = 0.0,
            trail_exit     = 0.0,
            unit_size      = 0.0,
            risk_amount    = 0.0,
            pyramid_levels = [],
            ema_21         = round(daily_dema, 5),
            ema_55         = 0.0,
            ema_200        = 0.0,
            adx            = 0.0,
            momentum_12m   = 0.0,
            momentum_3m    = 0.0,
            donchian_20_hi = 0.0,
            donchian_20_lo = 0.0,
            donchian_55_hi = 0.0,
            donchian_55_lo = 0.0,
            reason         = reason,
        )
