"""
Report generation for IG trading analytics.

Renders a full, colour-coded console report and exports data to CSV / JSON.

Sections printed
----------------
1.  Account summary
2.  Overall P&L
3.  Trade statistics
4.  Risk metrics (Sharpe, Sortino, Calmar …)
5.  Drawdown analysis
6.  Open positions
7.  P&L by instrument (top 15)
8.  P&L by direction (Long vs Short)
9.  Monthly P&L calendar
10. P&L by day-of-week
11. P&L by hour-of-day
12. Recent trades (last 20)
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _green(text: str) -> str:
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"


def _red(text: str) -> str:
    return f"{Fore.RED}{text}{Style.RESET_ALL}"


def _yellow(text: str) -> str:
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"


def _cyan(text: str) -> str:
    return f"{Fore.CYAN}{text}{Style.RESET_ALL}"


def _bold(text: str) -> str:
    return f"{Style.BRIGHT}{text}{Style.RESET_ALL}"


def _pnl_colour(value: float) -> str:
    formatted = f"{value:+,.2f}"
    return _green(formatted) if value > 0 else (_red(formatted) if value < 0 else formatted)


def _pct_colour(value: float) -> str:
    formatted = f"{value:.1f}%"
    return _green(formatted) if value >= 50 else _red(formatted)


def _section(title: str) -> None:
    width = 70
    print()
    print(_bold(_cyan("=" * width)))
    print(_bold(_cyan(f"  {title}")))
    print(_bold(_cyan("=" * width)))


def _subsection(title: str) -> None:
    print()
    print(_bold(f"  {title}"))
    print("  " + "-" * 50)


# ---------------------------------------------------------------------------
# Individual sections
# ---------------------------------------------------------------------------

def _print_account(accounts: List[Dict[str, Any]]) -> None:
    _section("ACCOUNT SUMMARY")
    if not accounts:
        print(_yellow("  No account data returned."))
        return

    rows = []
    for acc in accounts:
        bal = acc.get("balance", {})
        rows.append(
            [
                acc.get("accountId", ""),
                acc.get("accountName", ""),
                acc.get("accountType", ""),
                acc.get("currency", ""),
                f"{float(bal.get('balance', 0)):,.2f}",
                f"{float(bal.get('available', 0)):,.2f}",
                f"{float(bal.get('deposit', 0)):,.2f}",
                f"{float(bal.get('profitLoss', 0)):+,.2f}",
            ]
        )
    headers = ["ID", "Name", "Type", "CCY", "Balance", "Available", "Margin", "P&L"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _print_open_positions(positions_df: pd.DataFrame) -> None:
    _section("OPEN POSITIONS")
    if positions_df.empty:
        print(_yellow("  No open positions."))
        return

    rows = []
    for _, p in positions_df.iterrows():
        upl = float(p.get("unrealised_pnl", 0))
        rows.append(
            [
                str(p.get("instrument", ""))[:35],
                p.get("direction", ""),
                p.get("size", 0),
                p.get("open_level", 0),
                p.get("current_bid", 0),
                _pnl_colour(upl),
                p.get("currency", ""),
            ]
        )
    headers = ["Instrument", "Dir", "Size", "Open", "Current", "Unreal P&L", "CCY"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _print_pnl_metrics(m: Dict[str, Any]) -> None:
    _section("OVERALL P&L")
    net = float(m.get("net_pnl", 0))
    rows = [
        ["Net P&L",            _pnl_colour(net)],
        ["Gross Profit",       _green(f"+{m['gross_profit']:,.2f}")],
        ["Gross Loss",         _red(f"-{abs(m['gross_loss']):,.2f}")],
        ["Largest Single Win", _green(f"+{m['largest_win']:,.2f}")],
        ["Largest Single Loss",_red(f"{m['largest_loss']:,.2f}")],
        ["Average P&L / Trade",_pnl_colour(float(m["average_pnl_per_trade"]))],
        ["Average Win",        _green(f"+{m['average_win']:,.2f}")],
        ["Average Loss",       _red(f"-{abs(m['average_loss']):,.2f}")],
    ]
    print(tabulate(rows, tablefmt="plain"))


def _print_trade_stats(s: Dict[str, Any], summary: Dict[str, Any]) -> None:
    _section("TRADE STATISTICS")
    rows = [
        ["Total Trades",          summary.get("total_trades", 0)],
        ["  Winning",             _green(str(s["winning_trades"] if "winning_trades" in s else ""))],
        ["  Losing",              _red(str(s["losing_trades"]  if "losing_trades"  in s else ""))],
        ["  Breakeven",           s.get("breakeven_trades", 0)],
        ["Win Rate",              _pct_colour(float(s.get("win_rate_pct", 0)))],
        ["Profit Factor",         _bold(f"{s.get('profit_factor', 0):.3f}")],
        ["Expectancy / Trade",    _pnl_colour(float(s.get("expectancy", 0)))],
        ["Reward : Risk Ratio",   f"{s.get('reward_risk_ratio', 0):.3f}"],
        ["Kelly Criterion",       f"{s.get('kelly_criterion_pct', 0):.2f}%"],
        ["Max Consecutive Wins",  _green(str(s.get("max_consecutive_wins", 0)))],
        ["Max Consecutive Losses",_red(str(s.get("max_consecutive_losses", 0)))],
        ["Instruments Traded",    summary.get("instruments_traded", 0)],
        ["Period",                f"{summary.get('first_trade','')} → {summary.get('last_trade','')}"],
    ]
    # merge winning/losing into summary rows (flatten)
    pnl = s  # already flat since analytics returns flat dicts
    print(tabulate(rows, tablefmt="plain"))


def _print_risk_metrics(r: Dict[str, Any]) -> None:
    _section("RISK & RETURN METRICS")

    def _ratio_colour(v: float) -> str:
        v = float(v)
        if v >= 1.5:
            return _green(f"{v:.3f}")
        if v >= 0.5:
            return _yellow(f"{v:.3f}")
        return _red(f"{v:.3f}")

    rows = [
        ["Sharpe Ratio (annualised)",  _ratio_colour(r.get("sharpe_ratio", 0))],
        ["Sortino Ratio (annualised)", _ratio_colour(r.get("sortino_ratio", 0))],
        ["Calmar Ratio",               _ratio_colour(r.get("calmar_ratio", 0))],
        ["Annualised Return",          _pnl_colour(float(r.get("annualised_return", 0)))],
        ["Avg Daily P&L",              _pnl_colour(float(r.get("daily_pnl_mean", 0)))],
        ["Daily P&L Std Dev",          f"{r.get('daily_pnl_std', 0):,.2f}"],
        ["Trading Days",               r.get("trading_days", 0)],
    ]
    print(tabulate(rows, tablefmt="plain"))


def _print_drawdown(d: Dict[str, Any]) -> None:
    _section("DRAWDOWN ANALYSIS")
    rows = [
        ["Max Drawdown (absolute)",   _red(f"{d.get('max_drawdown_absolute', 0):,.2f}")],
        ["Max Drawdown (%)",          _red(f"{d.get('max_drawdown_pct', 0):.2f}%")],
        ["Average Drawdown",          f"{d.get('average_drawdown', 0):,.2f}"],
        ["Longest DD Streak (trades)",d.get("max_drawdown_duration_trades", 0)],
        ["Trades spent in drawdown",  d.get("total_drawdown_trades", 0)],
    ]
    print(tabulate(rows, tablefmt="plain"))


def _print_by_instrument(instruments: List[Dict[str, Any]]) -> None:
    _section("P&L BY INSTRUMENT  (top 15 by net P&L)")
    if not instruments:
        print(_yellow("  No data."))
        return

    rows = []
    for r in instruments[:15]:
        net = float(r["net_pnl"])
        rows.append(
            [
                str(r["instrument"])[:35],
                r["trades"],
                _pnl_colour(net),
                _pct_colour(float(r["win_rate_pct"])),
                f"{r['profit_factor']:.3f}",
                _pnl_colour(float(r["avg_pnl"])),
                _green(f"+{r['largest_win']:,.2f}"),
                _red(f"{r['largest_loss']:,.2f}"),
            ]
        )
    headers = ["Instrument", "Trades", "Net P&L", "Win%", "PF", "Avg P&L", "Best", "Worst"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _print_by_direction(directions: Dict[str, Any]) -> None:
    _section("P&L BY DIRECTION  (Long vs Short)")
    if not directions:
        print(_yellow("  No data."))
        return
    rows = []
    for direction, d in directions.items():
        rows.append(
            [
                direction,
                d["trades"],
                _pnl_colour(float(d["net_pnl"])),
                _pct_colour(float(d["win_rate_pct"])),
                f"{d['profit_factor']:.3f}",
            ]
        )
    headers = ["Direction", "Trades", "Net P&L", "Win%", "Profit Factor"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _print_monthly(monthly: List[Dict[str, Any]]) -> None:
    _section("MONTHLY P&L")
    if not monthly:
        print(_yellow("  No data."))
        return
    rows = []
    for m in monthly:
        net = float(m["net_pnl"])
        rows.append(
            [
                m["month"],
                m["trades"],
                _pnl_colour(net),
                _pct_colour(float(m["win_rate_pct"])),
            ]
        )
    headers = ["Month", "Trades", "Net P&L", "Win%"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _print_dow(dow: List[Dict[str, Any]]) -> None:
    _section("P&L BY DAY OF WEEK")
    if not dow:
        print(_yellow("  No data."))
        return
    rows = [
        [
            r["day"],
            r["trades"],
            _pnl_colour(float(r["net_pnl"])),
            _pct_colour(float(r["win_rate_pct"])),
            _pnl_colour(float(r["avg_pnl"])),
        ]
        for r in dow
    ]
    headers = ["Day", "Trades", "Net P&L", "Win%", "Avg P&L"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _print_by_hour(hours: List[Dict[str, Any]]) -> None:
    _section("P&L BY HOUR (UTC close time)")
    if not hours:
        print(_yellow("  No data."))
        return
    rows = [
        [
            f"{r['hour']:02d}:00",
            r["trades"],
            _pnl_colour(float(r["net_pnl"])),
            _pct_colour(float(r["win_rate_pct"])),
            _pnl_colour(float(r["avg_pnl"])),
        ]
        for r in hours
    ]
    headers = ["Hour (UTC)", "Trades", "Net P&L", "Win%", "Avg P&L"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


def _print_recent_trades(trades: List[Dict[str, Any]]) -> None:
    _section("RECENT TRADES  (last 20)")
    if not trades:
        print(_yellow("  No trade data."))
        return
    rows = []
    for t in trades:
        pnl = float(t.get("pnl", 0))
        result = t.get("result", "")
        result_str = _green(result) if result == "WIN" else (_red(result) if result == "LOSS" else result)
        rows.append(
            [
                str(t.get("date", ""))[:19],
                str(t.get("instrument", ""))[:28],
                t.get("direction", ""),
                t.get("size", 0),
                t.get("open_level", 0),
                t.get("close_level", 0),
                _pnl_colour(pnl),
                result_str,
            ]
        )
    headers = ["Date (UTC)", "Instrument", "Dir", "Size", "Open", "Close", "P&L", "Result"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def generate_console_report(
    analytics: Dict[str, Any],
    accounts: Optional[List[Dict[str, Any]]] = None,
    open_positions: Optional[pd.DataFrame] = None,
) -> None:
    """Print the full analytics report to stdout."""
    print()
    print(_bold(_cyan("╔══════════════════════════════════════════════════════════════════════╗")))
    print(_bold(_cyan("║   ███╗   ███╗██╗   ██╗     ██╗     ██████╗ █████╗ ██████╗           ║")))
    print(_bold(_cyan("║   ████╗ ████║╚██╗ ██╔╝     ██║    ██╔════╝██╔══██╗██╔══██╗          ║")))
    print(_bold(_cyan("║   ██╔████╔██║ ╚████╔╝      ██║    ██║     ███████║██████╔╝          ║")))
    print(_bold(_cyan("║   ██║╚██╔╝██║  ╚██╔╝       ██║    ██║     ██╔══██║██╔═══╝           ║")))
    print(_bold(_cyan("║   ██║ ╚═╝ ██║   ██║        ██║    ╚██████╗██║  ██║██║               ║")))
    print(_bold(_cyan("║   ╚═╝     ╚═╝   ╚═╝        ╚═╝     ╚═════╝╚═╝  ╚═╝╚═╝               ║")))
    print(_bold(_cyan("║                                                                      ║")))
    print(_bold(_cyan("║              MYJ CAPITAL  —  TRADING ANALYTICS REPORT               ║")))
    print(_bold(_cyan(f"║              Generated : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'):<45}║")))
    print(_bold(_cyan("╚══════════════════════════════════════════════════════════════════════╝")))

    if "error" in analytics:
        print(_red(f"\n  ERROR: {analytics['error']}"))
        return

    if accounts:
        _print_account(accounts)

    if open_positions is not None:
        _print_open_positions(open_positions)

    _print_pnl_metrics(analytics["pnl_metrics"])

    # Merge winning/losing counts into trade_statistics for display
    ts = {**analytics["trade_statistics"], **analytics["pnl_metrics"]}
    _print_trade_stats(ts, analytics["summary"])

    _print_risk_metrics(analytics["risk_metrics"])
    _print_drawdown(analytics["drawdown"])
    _print_by_instrument(analytics.get("by_instrument", []))
    _print_by_direction(analytics.get("by_direction", {}))
    _print_monthly(analytics.get("by_month", []))
    _print_dow(analytics.get("by_day_of_week", []))
    _print_by_hour(analytics.get("by_hour", []))
    _print_recent_trades(analytics.get("recent_trades", []))

    print()
    print(_bold(_cyan("=" * 70)))
    print(_bold(_cyan("  END OF REPORT")))
    print(_bold(_cyan("=" * 70)))
    print()


def export_transactions_csv(transactions_df: pd.DataFrame, output_dir: str) -> str:
    """Save transactions DataFrame to CSV. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"ig_transactions_{ts}.csv")
    transactions_df.to_csv(path, index=False)
    print(_green(f"  Transactions exported → {path}"))
    return path


def export_activity_csv(activity_df: pd.DataFrame, output_dir: str) -> str:
    """Save activity DataFrame to CSV. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"ig_activity_{ts}.csv")
    activity_df.to_csv(path, index=False)
    print(_green(f"  Activity exported     → {path}"))
    return path


def export_analytics_json(analytics: Dict[str, Any], output_dir: str) -> str:
    """Save the full analytics dict to JSON. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"ig_analytics_{ts}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(analytics, fh, indent=2, default=str)
    print(_green(f"  Analytics JSON        → {path}"))
    return path


def export_equity_curve_csv(equity_curve: List[Dict[str, Any]], output_dir: str) -> str:
    """Save equity curve data to CSV. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"ig_equity_curve_{ts}.csv")
    df = pd.DataFrame(equity_curve)
    df.to_csv(path, index=False)
    print(_green(f"  Equity curve          → {path}"))
    return path
