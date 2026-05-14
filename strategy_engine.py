"""
MYJ Capital — Strategy Engine
==============================

Implements the documented rules of the world's most successful CTA
trend-following hedge funds, combined into one robust system:

  • TURTLE SYSTEM (Richard Dennis / Eckhardt, 1983)
    — Donchian channel breakout entries (System 1: 20-day, System 2: 55-day)
    — ATR-based position sizing ("N" = 20-day ATR)
    — Stop loss at 2N, exit at 10/20-day channel reversal
    — Pyramid up to 4 units at 0.5N intervals

  • MAN AHL / WINTON APPROACH
    — Volatility targeting: scale positions inversely to volatility
    — Multi-signal blend: short + medium + long term trend
    — Portfolio heat management across correlated markets

  • AQR TIME-SERIES MOMENTUM (Moskowitz, Ooi, Pedersen 2012)
    — 12-month lookback momentum as primary filter
    — Quarterly (63-day) momentum as secondary filter

SIGNAL STRENGTH SCORING
-----------------------
Each market is scored 0–100:
  +20  System 1 breakout (20-day)
  +20  System 2 breakout (55-day) — stronger, longer signal
  +15  EMA 21 > EMA 55 (trend direction)
  +15  Price > EMA 200 (long-term trend filter)
  +15  ADX > 20 (trend is strong enough to trade)
  +15  12-month momentum aligned with direction
  ─────────────────────────────────────────────
  100  Maximum score = strongest possible signal

Score ≥ 50 → SIGNAL generated. Score < 50 → WAIT.

POSITION SIZING  (Turtle volatility-adjusted)
--------------------------------------------
  N            = ATR(20)
  Dollar Risk  = Account Equity × Risk %
  Unit Size    = Dollar Risk / (N × ATR_stop_multiplier × point_value)

  This ensures every trade risks exactly the same % of equity regardless
  of whether you are trading Gold at $3,300 or EUR/USD at 1.09.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import math


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class OHLC:
    date:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: float = 0.0


@dataclass
class Signal:
    """Output of the strategy engine for one market."""
    market_name:    str
    epic:           str
    direction:      str          # "LONG" | "SHORT" | "WAIT"
    system:         int          # 1 (20-day) or 2 (55-day)
    score:          int          # 0-100 signal strength
    current_price:  float
    atr:            float        # N — 20-day ATR
    entry_level:    float        # suggested entry (last Donchian breakout level)
    stop_loss:      float        # 2N from entry
    take_profit:    float        # 4N from entry
    trail_exit:     float        # 10-day channel level (System 1 exit)
    unit_size:      float        # £/point bet size for 1 unit (1% risk)
    risk_amount:    float        # £ risked on 1 unit
    pyramid_levels: List[float]  # price levels to add units (0.5N steps)
    ema_21:         float
    ema_55:         float
    ema_200:        float
    adx:            float
    momentum_12m:   float        # 12-month % return
    momentum_3m:    float        # 3-month % return
    donchian_20_hi: float
    donchian_20_lo: float
    donchian_55_hi: float
    donchian_55_lo: float
    reason:         str          # human-readable explanation


# ── Indicator calculations ────────────────────────────────────────────────────

def _ema(prices: List[float], period: int) -> List[float]:
    """Exponential moving average."""
    if len(prices) < period:
        return [float("nan")] * len(prices)
    k = 2.0 / (period + 1)
    result = [float("nan")] * (period - 1)
    result.append(sum(prices[:period]) / period)
    for p in prices[period:]:
        result.append(p * k + result[-1] * (1 - k))
    return result


def _atr(bars: List[OHLC], period: int = 20) -> List[float]:
    """Average True Range (Wilder smoothing)."""
    trs = [bars[0].high - bars[0].low]
    for i in range(1, len(bars)):
        h, l, pc = bars[i].high, bars[i].low, bars[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))

    result = [float("nan")] * (period - 1)
    result.append(sum(trs[:period]) / period)
    for tr in trs[period:]:
        result.append((result[-1] * (period - 1) + tr) / period)
    return result


def _donchian(bars: List[OHLC], period: int) -> tuple:
    """(highs_list, lows_list) — Donchian channel over rolling window."""
    highs = [float("nan")] * (period - 1)
    lows  = [float("nan")] * (period - 1)
    for i in range(period - 1, len(bars)):
        window = bars[i - period + 1 : i + 1]
        highs.append(max(b.high for b in window))
        lows.append(min(b.low  for b in window))
    return highs, lows


def _adx(bars: List[OHLC], period: int = 14) -> List[float]:
    """Average Directional Index (Wilder method)."""
    if len(bars) < period * 2:
        return [float("nan")] * len(bars)

    plus_dm, minus_dm, trs = [], [], []
    for i in range(1, len(bars)):
        up   = bars[i].high - bars[i - 1].high
        down = bars[i - 1].low - bars[i].low
        plus_dm.append(up   if up > down and up > 0   else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        h, l, pc = bars[i].high, bars[i].low, bars[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))

    def _wilder(data, p):
        out = [sum(data[:p])]
        for v in data[p:]:
            out.append(out[-1] - out[-1] / p + v)
        return out

    atr_w    = _wilder(trs,      period)
    plus_w   = _wilder(plus_dm,  period)
    minus_w  = _wilder(minus_dm, period)

    dx_list = []
    for a, p, m in zip(atr_w, plus_w, minus_w):
        if a == 0:
            dx_list.append(0.0)
            continue
        pdi  = 100 * p / a
        mdi  = 100 * m / a
        denom = pdi + mdi
        dx_list.append(100 * abs(pdi - mdi) / denom if denom else 0.0)

    adx_vals = [sum(dx_list[:period]) / period]
    for dx in dx_list[period:]:
        adx_vals.append((adx_vals[-1] * (period - 1) + dx) / period)

    pad = len(bars) - len(adx_vals)
    return [float("nan")] * pad + adx_vals


# ── Strategy engine ───────────────────────────────────────────────────────────

class TurtleCTAStrategy:
    """
    Multi-signal trend following strategy inspired by:
      - Turtle Trading (Dennis/Eckhardt)
      - Man AHL / Winton volatility targeting
      - AQR Time-Series Momentum

    Parameters
    ----------
    account_equity : float
        Current account balance in account currency.
    risk_pct : float
        Fraction of equity to risk per trade unit (default 0.01 = 1%).
    atr_stop : float
        Stop distance in ATR multiples (default 2.0).
    atr_target : float
        Take-profit distance in ATR multiples (default 4.0).
    min_adx : float
        Minimum ADX required to take a signal (default 20).
    min_score : int
        Minimum signal score (0-100) required (default 50).
    """

    def __init__(
        self,
        account_equity: float,
        risk_pct:   float = 0.01,
        atr_stop:   float = 2.0,
        atr_target: float = 4.0,
        min_adx:    float = 20.0,
        min_score:  int   = 30,
    ):
        self.equity     = account_equity
        self.risk_pct   = risk_pct
        self.atr_stop   = atr_stop
        self.atr_target = atr_target
        self.min_adx    = min_adx
        self.min_score  = min_score

    def analyse(self, bars: List[OHLC], market: dict) -> Signal:
        """
        Run all indicators and generate a Signal for one market.

        Parameters
        ----------
        bars   : at least 300 daily OHLC bars, oldest first
        market : dict from markets_config.MARKETS
        """
        if len(bars) < 60:
            return self._no_signal(market, bars[-1].close if bars else 0,
                                   "Not enough data (need 60+ daily bars)")

        closes = [b.close for b in bars]
        highs  = [b.high  for b in bars]
        lows   = [b.low   for b in bars]

        # ── Indicators ──────────────────────────────────────────────────────
        atr_series   = _atr(bars, 20)
        ema21_series = _ema(closes, 21)
        ema55_series = _ema(closes, 55)
        ema200_series= _ema(closes, 200)
        adx_series   = _adx(bars, 14)

        dc20_hi, dc20_lo = _donchian(bars, 20)
        dc55_hi, dc55_lo = _donchian(bars, 55)
        dc10_hi, dc10_lo = _donchian(bars, 10)  # System-1 exit channel

        # ── Latest values ────────────────────────────────────────────────────
        price    = closes[-1]
        atr      = atr_series[-1]
        ema21    = ema21_series[-1]
        ema55    = ema55_series[-1]
        ema200   = ema200_series[-1] if len(bars) >= 200 else float("nan")
        adx      = adx_series[-1]
        d20h     = dc20_hi[-1];  d20l = dc20_lo[-1]
        d55h     = dc55_hi[-1];  d55l = dc55_lo[-1]
        d10h     = dc10_hi[-1];  d10l = dc10_lo[-1]

        # ── Momentum ─────────────────────────────────────────────────────────
        mom_12m = ((closes[-1] / closes[-252]) - 1) * 100 if len(closes) >= 252 else 0.0
        mom_3m  = ((closes[-1] / closes[-63])  - 1) * 100 if len(closes) >= 63  else 0.0

        # ── Guard: skip NaN ──────────────────────────────────────────────────
        if math.isnan(atr) or atr == 0 or math.isnan(d20h):
            return self._no_signal(market, price, "Indicators not ready")

        # ── Determine direction preference ───────────────────────────────────
        # Long bias: price above both EMAs and momentum positive
        # Short bias: price below both EMAs and momentum negative
        long_bias  = (ema21 > ema55) and (mom_12m > 0)
        short_bias = (ema21 < ema55) and (mom_12m < 0)

        # ── System 1: 20-day Donchian breakout ───────────────────────────────
        sys1_long  = price >= d20h
        sys1_short = price <= d20l

        # ── System 2: 55-day Donchian breakout ───────────────────────────────
        sys2_long  = price >= d55h
        sys2_short = price <= d55l

        # ── Score the signal (0-100) ─────────────────────────────────────────
        def _score(direction: str) -> int:
            s = 0
            if direction == "LONG":
                if sys1_long:  s += 20
                if sys2_long:  s += 20
                if ema21 > ema55:                     s += 15
                if not math.isnan(ema200) and price > ema200: s += 15
                if adx > self.min_adx:                s += 15
                if mom_12m > 0:                       s += 15
            else:
                if sys1_short: s += 20
                if sys2_short: s += 20
                if ema21 < ema55:                     s += 15
                if not math.isnan(ema200) and price < ema200: s += 15
                if adx > self.min_adx:                s += 15
                if mom_12m < 0:                       s += 15
            return s

        long_score  = _score("LONG")
        short_score = _score("SHORT")

        # ── Pick best direction ───────────────────────────────────────────────
        if long_score >= short_score and long_score >= self.min_score:
            direction   = "LONG"
            score       = long_score
            system      = 2 if sys2_long else 1
            entry       = d20h if system == 1 else d55h
            stop        = entry - self.atr_stop   * atr
            target      = entry + self.atr_target * atr
            trail_exit  = d10l      # System 1 trail exit
            pyramid     = [entry + i * 0.5 * atr for i in range(1, 5)]
            reason      = self._build_reason("LONG", sys1_long, sys2_long,
                                              ema21>ema55, adx, mom_12m, ema200, price)
        elif short_score > long_score and short_score >= self.min_score:
            direction   = "SHORT"
            score       = short_score
            system      = 2 if sys2_short else 1
            entry       = d20l if system == 1 else d55l
            stop        = entry + self.atr_stop   * atr
            target      = entry - self.atr_target * atr
            trail_exit  = d10h
            pyramid     = [entry - i * 0.5 * atr for i in range(1, 5)]
            reason      = self._build_reason("SHORT", sys1_short, sys2_short,
                                              ema21<ema55, adx, mom_12m, ema200, price)
        else:
            return self._no_signal(
                market, price,
                f"No breakout (score L={long_score} S={short_score} < {self.min_score})"
            )

        # ── Position sizing (Turtle: 1% equity / 2N) ─────────────────────────
        risk_amount = self.equity * self.risk_pct
        stop_distance = abs(entry - stop)
        unit_size = risk_amount / stop_distance if stop_distance > 0 else market["min_size"]
        unit_size = max(unit_size, market["min_size"])

        return Signal(
            market_name    = market["name"],
            epic           = market["epic"],
            direction      = direction,
            system         = system,
            score          = score,
            current_price  = round(price, 5),
            atr            = round(atr, 5),
            entry_level    = round(entry, 5),
            stop_loss      = round(stop, 5),
            take_profit    = round(target, 5),
            trail_exit     = round(trail_exit, 5),
            unit_size      = round(unit_size, 2),
            risk_amount    = round(risk_amount, 2),
            pyramid_levels = [round(p, 5) for p in pyramid],
            ema_21         = round(ema21, 5),
            ema_55         = round(ema55, 5),
            ema_200        = round(ema200, 5) if not math.isnan(ema200) else 0.0,
            adx            = round(adx, 2),
            momentum_12m   = round(mom_12m, 2),
            momentum_3m    = round(mom_3m, 2),
            donchian_20_hi = round(d20h, 5),
            donchian_20_lo = round(d20l, 5),
            donchian_55_hi = round(d55h, 5),
            donchian_55_lo = round(d55l, 5),
            reason         = reason,
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _no_signal(self, market: dict, price: float, reason: str) -> Signal:
        return Signal(
            market_name=market["name"], epic=market["epic"],
            direction="WAIT", system=0, score=0,
            current_price=round(price, 5), atr=0, entry_level=price,
            stop_loss=0, take_profit=0, trail_exit=0,
            unit_size=0, risk_amount=0, pyramid_levels=[],
            ema_21=0, ema_55=0, ema_200=0, adx=0,
            momentum_12m=0, momentum_3m=0,
            donchian_20_hi=0, donchian_20_lo=0,
            donchian_55_hi=0, donchian_55_lo=0,
            reason=reason,
        )

    @staticmethod
    def _build_reason(direction, sys1, sys2, ema_ok, adx, mom12, ema200, price) -> str:
        parts = []
        if sys2: parts.append("55-day breakout ✓")
        elif sys1: parts.append("20-day breakout ✓")
        if ema_ok: parts.append("EMA trend ✓")
        if adx > 20: parts.append(f"ADX {adx:.1f} ✓")
        m = f"{mom12:+.1f}%"
        parts.append(f"12m momentum {m} ✓" if (direction=="LONG" and mom12>0) or
                     (direction=="SHORT" and mom12<0) else f"12m momentum {m}")
        return " | ".join(parts)
