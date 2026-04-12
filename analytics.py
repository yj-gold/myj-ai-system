"""
Trading strategy analytics engine.

Given a DataFrame of closed transactions (from DataExtractor.get_transactions),
calculates every relevant metric for evaluating strategy profitability:

  • Overall P&L metrics
  • Trade statistics (win rate, profit factor, expectancy …)
  • Drawdown analysis (max drawdown, avg drawdown, recovery)
  • Sharpe / Sortino ratios
  • Consecutive wins / losses
  • Breakdown by instrument, direction, month, day-of-week, hour

All monetary values are in the account's native currency (as returned by IG).
"""

import math
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def _max_drawdown(cumulative_pnl: pd.Series) -> Tuple[float, float]:
    """
    Return (max_drawdown_absolute, max_drawdown_pct) from a cumulative P&L series.

    max_drawdown_absolute: largest peak-to-trough drop in currency units
    max_drawdown_pct     : that drop expressed as % of the peak
    """
    running_max = cumulative_pnl.cummax()
    drawdown = cumulative_pnl - running_max          # always <= 0
    max_dd_abs = float(drawdown.min())               # most negative value

    # express as percentage of peak
    pct_dd = (drawdown / running_max.replace(0, float("nan"))) * 100
    max_dd_pct = float(pct_dd.min()) if not pct_dd.isna().all() else 0.0

    return max_dd_abs, max_dd_pct


def _consecutive_streaks(win_flags: pd.Series) -> Tuple[int, int]:
    """Return (max_consecutive_wins, max_consecutive_losses)."""
    max_wins = max_losses = cur_wins = cur_losses = 0
    for win in win_flags:
        if win:
            cur_wins += 1
            cur_losses = 0
        else:
            cur_losses += 1
            cur_wins = 0
        max_wins = max(max_wins, cur_wins)
        max_losses = max(max_losses, cur_losses)
    return max_wins, max_losses


def _sharpe(daily_pnl: pd.Series, periods_per_year: int = 252) -> float:
    """Annualised Sharpe ratio (assuming risk-free rate = 0)."""
    if len(daily_pnl) < 2:
        return 0.0
    std = daily_pnl.std()
    if std == 0:
        return 0.0
    return float((daily_pnl.mean() / std) * math.sqrt(periods_per_year))


def _sortino(daily_pnl: pd.Series, periods_per_year: int = 252) -> float:
    """Annualised Sortino ratio (downside deviation, risk-free = 0)."""
    if len(daily_pnl) < 2:
        return 0.0
    downside = daily_pnl[daily_pnl < 0]
    if len(downside) == 0:
        return float("inf")
    downside_std = downside.std()
    if downside_std == 0:
        return 0.0
    return float((daily_pnl.mean() / downside_std) * math.sqrt(periods_per_year))


# ---------------------------------------------------------------------------
# Main analytics class
# ---------------------------------------------------------------------------

class TradingAnalytics:
    """
    Compute all metrics from a transactions DataFrame.

    Parameters
    ----------
    transactions : pd.DataFrame
        Output of DataExtractor.get_transactions().  Must contain at minimum
        the columns: close_date, pnl, instrument, direction, size,
        open_level, close_level.
    """

    def __init__(self, transactions: pd.DataFrame) -> None:
        # Work only with closed DEAL rows (exclude deposits / withdrawals)
        df = transactions.copy()
        if "transaction_type" in df.columns:
            df = df[df["transaction_type"].isin(["DEAL", "TRADE", ""])].copy()

        df = df.dropna(subset=["pnl"]).copy()
        df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0.0)

        self._df = df

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def calculate_all(self) -> Dict[str, Any]:
        """Run every metric and return a single nested dict."""
        if self._df.empty:
            return {"error": "No transaction data available for the requested period."}

        return {
            "summary":           self._summary(),
            "pnl_metrics":       self._pnl_metrics(),
            "trade_statistics":  self._trade_statistics(),
            "risk_metrics":      self._risk_metrics(),
            "drawdown":          self._drawdown_analysis(),
            "by_instrument":     self._by_instrument(),
            "by_direction":      self._by_direction(),
            "by_month":          self._by_month(),
            "by_day_of_week":    self._by_day_of_week(),
            "by_hour":           self._by_hour(),
            "equity_curve":      self._equity_curve(),
            "recent_trades":     self._recent_trades(n=20),
        }

    # ------------------------------------------------------------------
    # Individual sections
    # ------------------------------------------------------------------

    def _summary(self) -> Dict[str, Any]:
        df = self._df
        close_dates = df["close_date"].dropna()
        return {
            "total_trades":    len(df),
            "first_trade":     str(close_dates.min()) if not close_dates.empty else None,
            "last_trade":      str(close_dates.max()) if not close_dates.empty else None,
            "instruments_traded": int(df["instrument"].nunique()),
            "currencies":      list(df["currency"].unique()) if "currency" in df.columns else [],
        }

    def _pnl_metrics(self) -> Dict[str, Any]:
        df = self._df
        pnl = df["pnl"]
        winners = pnl[pnl > 0]
        losers  = pnl[pnl < 0]
        breakeven = pnl[pnl == 0]

        gross_profit = float(winners.sum())
        gross_loss   = float(abs(losers.sum()))
        net_pnl      = float(pnl.sum())

        return {
            "net_pnl":         round(net_pnl, 2),
            "gross_profit":    round(gross_profit, 2),
            "gross_loss":      round(gross_loss, 2),
            "largest_win":     round(float(winners.max()), 2) if not winners.empty else 0.0,
            "largest_loss":    round(float(losers.min()), 2) if not losers.empty else 0.0,
            "average_pnl_per_trade": round(_safe_div(net_pnl, len(df)), 2),
            "average_win":     round(_safe_div(gross_profit, len(winners)), 2),
            "average_loss":    round(_safe_div(gross_loss, len(losers)), 2),
            "winning_trades":  int(len(winners)),
            "losing_trades":   int(len(losers)),
            "breakeven_trades": int(len(breakeven)),
        }

    def _trade_statistics(self) -> Dict[str, Any]:
        df = self._df
        pnl = df["pnl"]
        n = len(df)
        winners = pnl[pnl > 0]
        losers  = pnl[pnl < 0]

        win_rate  = _safe_div(len(winners), n) * 100
        loss_rate = _safe_div(len(losers),  n) * 100

        gross_profit = float(winners.sum())
        gross_loss   = float(abs(losers.sum()))
        profit_factor = _safe_div(gross_profit, gross_loss)

        avg_win  = _safe_div(gross_profit, len(winners)) if len(winners) else 0.0
        avg_loss = _safe_div(gross_loss,   len(losers))  if len(losers)  else 0.0

        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        expectancy = (win_rate / 100 * avg_win) - (loss_rate / 100 * avg_loss)

        # Reward:Risk ratio
        reward_risk = _safe_div(avg_win, avg_loss)

        # Kelly Criterion (% of capital to risk per trade)
        kelly = (win_rate / 100) - _safe_div(loss_rate / 100, reward_risk) if reward_risk else 0.0

        max_wins, max_losses = _consecutive_streaks(pnl > 0)

        return {
            "win_rate_pct":         round(win_rate, 2),
            "loss_rate_pct":        round(loss_rate, 2),
            "profit_factor":        round(profit_factor, 3),
            "expectancy":           round(expectancy, 2),
            "reward_risk_ratio":    round(reward_risk, 3),
            "kelly_criterion_pct":  round(kelly * 100, 2),
            "max_consecutive_wins":  max_wins,
            "max_consecutive_losses": max_losses,
        }

    def _risk_metrics(self) -> Dict[str, Any]:
        df = self._df.copy()
        df = df.dropna(subset=["close_date"]).sort_values("close_date")

        # Daily P&L aggregation for ratio calculations
        df["date_only"] = df["close_date"].dt.date
        daily = df.groupby("date_only")["pnl"].sum()

        sharpe  = _sharpe(daily)
        sortino = _sortino(daily)

        # Calmar ratio = annualised return / max drawdown (absolute)
        cum_pnl = df["pnl"].cumsum()
        max_dd_abs, max_dd_pct = _max_drawdown(cum_pnl)
        annualised_return = float(daily.mean() * 252)
        calmar = _safe_div(annualised_return, abs(max_dd_abs))

        return {
            "sharpe_ratio":   round(sharpe,  3),
            "sortino_ratio":  round(sortino, 3),
            "calmar_ratio":   round(calmar,  3),
            "annualised_return": round(annualised_return, 2),
            "daily_pnl_std":  round(float(daily.std()), 2),
            "daily_pnl_mean": round(float(daily.mean()), 2),
            "trading_days":   int(daily.shape[0]),
        }

    def _drawdown_analysis(self) -> Dict[str, Any]:
        df = self._df.copy()
        df = df.dropna(subset=["close_date"]).sort_values("close_date")
        cum_pnl = df["pnl"].cumsum()

        max_dd_abs, max_dd_pct = _max_drawdown(cum_pnl)

        # Average drawdown (only during drawdown periods)
        running_max = cum_pnl.cummax()
        dd_series = cum_pnl - running_max
        in_drawdown = dd_series[dd_series < 0]
        avg_dd = float(in_drawdown.mean()) if not in_drawdown.empty else 0.0

        # Drawdown duration: longest continuous period below peak
        in_dd_bool = dd_series < 0
        max_duration_trades = 0
        cur_duration = 0
        for flag in in_dd_bool:
            if flag:
                cur_duration += 1
                max_duration_trades = max(max_duration_trades, cur_duration)
            else:
                cur_duration = 0

        return {
            "max_drawdown_absolute": round(max_dd_abs, 2),
            "max_drawdown_pct":      round(max_dd_pct, 2),
            "average_drawdown":      round(avg_dd, 2),
            "max_drawdown_duration_trades": max_duration_trades,
            "total_drawdown_trades": int(in_drawdown.shape[0]),
        }

    def _by_instrument(self) -> List[Dict[str, Any]]:
        df = self._df.copy()
        rows = []
        for instrument, grp in df.groupby("instrument"):
            pnl = grp["pnl"]
            winners = pnl[pnl > 0]
            losers  = pnl[pnl < 0]
            rows.append(
                {
                    "instrument":    str(instrument),
                    "trades":        int(len(grp)),
                    "net_pnl":       round(float(pnl.sum()), 2),
                    "win_rate_pct":  round(_safe_div(len(winners), len(grp)) * 100, 1),
                    "profit_factor": round(
                        _safe_div(float(winners.sum()), float(abs(losers.sum()))), 3
                    ),
                    "avg_pnl":       round(_safe_div(float(pnl.sum()), len(grp)), 2),
                    "largest_win":   round(float(winners.max()), 2) if not winners.empty else 0.0,
                    "largest_loss":  round(float(losers.min()), 2) if not losers.empty else 0.0,
                }
            )
        rows.sort(key=lambda r: r["net_pnl"], reverse=True)
        return rows

    def _by_direction(self) -> Dict[str, Dict[str, Any]]:
        df = self._df.copy()
        result = {}
        for direction, grp in df.groupby("direction"):
            pnl = grp["pnl"]
            winners = pnl[pnl > 0]
            losers  = pnl[pnl < 0]
            result[str(direction)] = {
                "trades":        int(len(grp)),
                "net_pnl":       round(float(pnl.sum()), 2),
                "win_rate_pct":  round(_safe_div(len(winners), len(grp)) * 100, 1),
                "profit_factor": round(
                    _safe_div(float(winners.sum()), float(abs(losers.sum()))), 3
                ),
            }
        return result

    def _by_month(self) -> List[Dict[str, Any]]:
        df = self._df.copy()
        df = df.dropna(subset=["close_date"])
        df["month"] = df["close_date"].dt.to_period("M").astype(str)
        rows = []
        for month, grp in df.groupby("month"):
            pnl = grp["pnl"]
            winners = pnl[pnl > 0]
            rows.append(
                {
                    "month":        str(month),
                    "trades":       int(len(grp)),
                    "net_pnl":      round(float(pnl.sum()), 2),
                    "win_rate_pct": round(_safe_div(len(winners), len(grp)) * 100, 1),
                }
            )
        rows.sort(key=lambda r: r["month"])
        return rows

    def _by_day_of_week(self) -> List[Dict[str, Any]]:
        df = self._df.copy()
        df = df.dropna(subset=["close_date"])
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        df["dow"] = df["close_date"].dt.dayofweek
        rows = []
        for dow in range(7):
            grp = df[df["dow"] == dow]
            if grp.empty:
                continue
            pnl = grp["pnl"]
            winners = pnl[pnl > 0]
            rows.append(
                {
                    "day":          day_names[dow],
                    "trades":       int(len(grp)),
                    "net_pnl":      round(float(pnl.sum()), 2),
                    "win_rate_pct": round(_safe_div(len(winners), len(grp)) * 100, 1),
                    "avg_pnl":      round(_safe_div(float(pnl.sum()), len(grp)), 2),
                }
            )
        return rows

    def _by_hour(self) -> List[Dict[str, Any]]:
        df = self._df.copy()
        df = df.dropna(subset=["close_date"])
        df["hour"] = df["close_date"].dt.hour
        rows = []
        for hour, grp in df.groupby("hour"):
            pnl = grp["pnl"]
            winners = pnl[pnl > 0]
            rows.append(
                {
                    "hour":         int(hour),
                    "trades":       int(len(grp)),
                    "net_pnl":      round(float(pnl.sum()), 2),
                    "win_rate_pct": round(_safe_div(len(winners), len(grp)) * 100, 1),
                    "avg_pnl":      round(_safe_div(float(pnl.sum()), len(grp)), 2),
                }
            )
        rows.sort(key=lambda r: r["hour"])
        return rows

    def _equity_curve(self) -> List[Dict[str, Any]]:
        """Return cumulative P&L series (one point per trade)."""
        df = self._df.copy()
        df = df.dropna(subset=["close_date"]).sort_values("close_date")
        df["cumulative_pnl"] = df["pnl"].cumsum()
        running_max = df["cumulative_pnl"].cummax()
        df["drawdown"] = df["cumulative_pnl"] - running_max

        return [
            {
                "trade_num":      int(i + 1),
                "date":           str(row["close_date"]),
                "instrument":     str(row.get("instrument", "")),
                "pnl":            round(float(row["pnl"]), 2),
                "cumulative_pnl": round(float(row["cumulative_pnl"]), 2),
                "drawdown":       round(float(row["drawdown"]), 2),
            }
            for i, (_, row) in enumerate(df.iterrows())
        ]

    def _recent_trades(self, n: int = 20) -> List[Dict[str, Any]]:
        df = self._df.copy()
        df = df.dropna(subset=["close_date"]).sort_values("close_date", ascending=False)
        rows = []
        for _, row in df.head(n).iterrows():
            rows.append(
                {
                    "date":       str(row.get("close_date", "")),
                    "instrument": str(row.get("instrument", "")),
                    "direction":  str(row.get("direction", "")),
                    "size":       row.get("size", 0),
                    "open_level": row.get("open_level", 0),
                    "close_level":row.get("close_level", 0),
                    "pnl":        round(float(row.get("pnl", 0)), 2),
                    "result":     "WIN" if float(row.get("pnl", 0)) > 0
                                  else ("LOSS" if float(row.get("pnl", 0)) < 0 else "BE"),
                }
            )
        return rows
