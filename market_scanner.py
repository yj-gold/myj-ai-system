#!/usr/bin/env python3
"""
MYJ Capital — Market Scanner
==============================

Fetches 300 days of daily OHLC data from IG for every market in
markets_config.MARKETS, runs the TurtleCTA strategy engine, and
outputs a ranked signal table.

  GREEN  = LONG signal    RED = SHORT signal    GREY = WAIT

Usage
-----
  python market_scanner.py                  # scan all markets
  python market_scanner.py --search "Gold"  # find epic codes for a market
  python market_scanner.py --min-score 70   # only show high-conviction signals
  python market_scanner.py --no-email       # skip email alert
  python market_scanner.py --save           # save signals to CSV

The scanner does NOT place any trades automatically.
Every signal shows you: entry price, stop loss, take profit, and
exact position size (£/point) to risk 1% of your account equity.
You decide whether to act on it.
"""

import argparse
import csv
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tabulate import tabulate
from colorama import Fore, Style, init as colorama_init

import config
from ig_client import IGClient, IGAPIError
from markets_config import MARKETS, DEFAULT_RISK_PCT
from strategy_engine import TurtleCTAStrategy, OHLC, Signal
from trade_executor import TradeExecutor

colorama_init(autoreset=True)
logger = logging.getLogger(__name__)


# ── Colour helpers ────────────────────────────────────────────────────────────
def _g(t): return f"{Fore.GREEN}{t}{Style.RESET_ALL}"
def _r(t): return f"{Fore.RED}{t}{Style.RESET_ALL}"
def _y(t): return f"{Fore.YELLOW}{t}{Style.RESET_ALL}"
def _c(t): return f"{Fore.CYAN}{t}{Style.RESET_ALL}"
def _b(t): return f"{Style.BRIGHT}{t}{Style.RESET_ALL}"

def _dir_color(d):
    if d == "LONG":  return _g(f"▲ {d}")
    if d == "SHORT": return _r(f"▼ {d}")
    return _y("◆ WAIT")

def _score_color(s):
    if s >= 80: return _g(f"{s}/100")
    if s >= 60: return _y(f"{s}/100")
    if s >  0:  return f"{s}/100"
    return "—"


# ── IG price fetcher ──────────────────────────────────────────────────────────

def fetch_ohlc(client: IGClient, epic: str, days: int = 310) -> List[OHLC]:
    """Fetch daily OHLC bars from IG for the past `days` calendar days."""
    to_dt   = datetime.utcnow()
    from_dt = to_dt - timedelta(days=days)

    params = {
        "resolution": "DAY",
        "from":       from_dt.strftime("%Y-%m-%dT00:00:00"),
        "to":         to_dt.strftime("%Y-%m-%dT23:59:59"),
        "max":        500,
    }

    try:
        body = client.get(f"/prices/{epic}", version=3, params=params)
    except IGAPIError as exc:
        logger.warning("Could not fetch %s: %s", epic, exc)
        return []

    raw = body.get("prices", [])
    bars = []
    for p in raw:
        mid_close = p.get("closePrice", {})
        mid_open  = p.get("openPrice",  {})
        mid_high  = p.get("highPrice",  {})
        mid_low   = p.get("lowPrice",   {})

        def _mid(d):
            if d.get("mid") is not None:
                return float(d["mid"])
            bid = d.get("bid")
            ask = d.get("ask")
            if bid is not None and ask is not None:
                return (float(bid) + float(ask)) / 2
            return float(bid or ask or 0)

        c = _mid(mid_close)
        if c == 0:
            continue
        bars.append(OHLC(
            date   = p.get("snapshotTime", ""),
            open   = _mid(mid_open),
            high   = _mid(mid_high),
            low    = _mid(mid_low),
            close  = c,
            volume = float(p.get("lastTradedVolume", 0) or 0),
        ))
    return bars


def fetch_account_equity(client: IGClient) -> float:
    """Return the current account balance (used for position sizing)."""
    try:
        body = client.get("/accounts", version=1)
        accounts = body.get("accounts", [])
        for acc in accounts:
            bal = acc.get("balance", {})
            v   = bal.get("balance") or bal.get("available")
            if v is not None:
                return float(v)
    except Exception:
        pass
    return 10_000.0  # fallback — user should set this explicitly


def search_epics(client: IGClient, term: str) -> None:
    """Print markets matching a search term with their epic codes."""
    body = client.get("/markets", version=1, params={"searchTerm": term})
    markets = body.get("markets", [])
    if not markets:
        print(_y(f"No markets found for '{term}'"))
        return
    rows = []
    for m in markets[:30]:
        rows.append([
            m.get("instrumentName", "")[:40],
            m.get("epic", ""),
            m.get("instrumentType", ""),
            m.get("expiry", "-"),
        ])
    print(tabulate(rows, headers=["Name", "Epic", "Type", "Expiry"],
                   tablefmt="rounded_outline"))


# ── Signal display ────────────────────────────────────────────────────────────

def print_signal_table(signals: List[Signal]) -> None:
    active = [s for s in signals if s.direction != "WAIT"]
    waiting= [s for s in signals if s.direction == "WAIT"]

    print()
    print(_b(_c("=" * 80)))
    print(_b(_c("  MYJ CAPITAL  —  MARKET SCANNER  |  CTA Trend-Following Strategy")))
    print(_b(_c(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  |  "
               f"Signals: {len(active)}  |  Markets scanned: {len(signals)}")))
    print(_b(_c("=" * 80)))

    if not active:
        print(_y("\n  No signals at this time. Markets are in consolidation.\n"))
    else:
        print(_b(f"\n  ▶  ACTIVE SIGNALS ({len(active)})\n"))
        rows = []
        for s in sorted(active, key=lambda x: -x.score):
            rows.append([
                _b(s.market_name[:22]),
                _dir_color(s.direction),
                f"Sys {s.system}",
                _score_color(s.score),
                f"{s.current_price:,.4f}",
                f"{s.entry_level:,.4f}",
                _r(f"{s.stop_loss:,.4f}"),
                _g(f"{s.take_profit:,.4f}"),
                f"£{s.unit_size:.2f}/pt",
                _r(f"-£{s.risk_amount:.0f}"),
                f"{s.adx:.1f}",
                f"{s.momentum_12m:+.1f}%",
            ])
        headers = ["Market","Dir","Sys","Score","Price","Entry","Stop",
                   "Target","Size","Risk","ADX","12m Mom"]
        print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))

        # Detailed breakdown for each signal
        print()
        for s in sorted(active, key=lambda x: -x.score):
            col = _g if s.direction == "LONG" else _r
            print(col(f"  {'▲' if s.direction == 'LONG' else '▼'} {s.market_name}") +
                  f"  [{s.reason}]")
            print(f"     Entry: {s.entry_level:,.5f}  |  "
                  f"Stop: {s.stop_loss:,.5f}  |  "
                  f"Target: {s.take_profit:,.5f}  |  "
                  f"Trail exit: {s.trail_exit:,.5f}")
            if s.pyramid_levels:
                plevels = "  →  ".join(f"{p:,.4f}" for p in s.pyramid_levels[:4])
                print(f"     Pyramid (add units at): {plevels}")
            print(f"     Position size: £{s.unit_size:.2f}/point  "
                  f"(1 unit = £{s.risk_amount:.0f} risk at 1%)")
            print()

    # Waiting markets (compact)
    if waiting:
        print(_b(f"  ◆  WAITING / NO SIGNAL ({len(waiting)})\n"))
        rows = []
        for s in waiting:
            rows.append([
                s.market_name[:25],
                f"{s.current_price:,.4f}",
                f"{s.adx:.1f}",
                f"{s.momentum_12m:+.1f}%",
                s.reason[:55],
            ])
        headers = ["Market", "Price", "ADX", "12m Mom", "Reason"]
        print(tabulate(rows, headers=headers, tablefmt="plain"))

    print()
    print(_b(_c("=" * 80)))
    print(_b(_c("  RISK REMINDER")))
    print(_b(_c("=" * 80)))
    print("  • Each unit risks 1% of account equity — never risk more")
    print("  • Max 4 units per market (Turtle rule)")
    print("  • Cut losses at stop, let winners trail to target")
    print("  • This scanner generates signals only — YOU decide to trade")
    print()


def save_signals_csv(signals: List[Signal], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"signals_{ts}.csv")
    fields = [
        "market_name","epic","direction","system","score","current_price",
        "atr","entry_level","stop_loss","take_profit","trail_exit",
        "unit_size","risk_amount","ema_21","ema_55","ema_200","adx",
        "momentum_12m","momentum_3m","donchian_20_hi","donchian_20_lo",
        "donchian_55_hi","donchian_55_lo","reason",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for s in signals:
            w.writerow(s.__dict__)
    print(_g(f"  Signals saved → {path}"))
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="MYJ Capital market scanner")
    p.add_argument("--search",    metavar="TERM",
                   help="Search IG for markets matching TERM and print their epic codes")
    p.add_argument("--min-score", type=int, default=50,
                   help="Only show signals with score >= this (default 50)")
    p.add_argument("--risk-pct",  type=float, default=DEFAULT_RISK_PCT,
                   help=f"% of equity to risk per trade unit (default {DEFAULT_RISK_PCT})")
    p.add_argument("--save",      action="store_true",
                   help="Save signals to CSV in ./output/")
    p.add_argument("--no-email",  action="store_true",
                   help="Skip sending email alert")
    p.add_argument("--execute",   action="store_true",
                   help="Auto-execute qualifying signals on IG (use with --demo to test)")
    p.add_argument("--exec-min-score", type=int, default=65,
                   help="Minimum score to auto-execute a trade (default 65)")
    p.add_argument("--dry-run",   action="store_true",
                   help="Show what would be traded without placing real orders")
    p.add_argument("--demo",      action="store_true",
                   help="Use IG demo endpoint")
    p.add_argument("--debug",     action="store_true",
                   help="Verbose logging")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    base_url = config.BASE_URL_DEMO if args.demo else config.BASE_URL
    client   = IGClient(base_url=base_url)

    try:
        client.login()

        # ── Epic search mode ─────────────────────────────────────────────────
        if args.search:
            print(f"\n  Searching IG for: '{args.search}' …\n")
            search_epics(client, args.search)
            return

        # ── Get account equity for position sizing ───────────────────────────
        equity = fetch_account_equity(client)
        print(f"\n  Account equity  : £{equity:,.2f}")
        print(f"  Risk per trade  : {args.risk_pct:.1f}%  (£{equity * args.risk_pct / 100:,.2f} per unit)")
        print(f"  Markets to scan : {len(MARKETS)}")
        print(f"  Min signal score: {args.min_score}/100\n")

        strategy = TurtleCTAStrategy(
            account_equity = equity,
            risk_pct       = args.risk_pct / 100,
            min_score      = args.min_score,
        )

        # ── Scan each market ─────────────────────────────────────────────────
        signals: List[Signal] = []
        for i, market in enumerate(MARKETS, 1):
            print(f"  [{i:02d}/{len(MARKETS)}] Scanning {market['name']:<20} ", end="", flush=True)
            bars = fetch_ohlc(client, market["epic"], days=400)
            if not bars:
                print(_y("no data"))
                signals.append(strategy._no_signal(market, 0, "No data from IG"))
                continue

            sig = strategy.analyse(bars, market)
            signals.append(sig)

            if sig.direction == "LONG":
                print(_g(f"▲ LONG   score={sig.score}/100  ADX={sig.adx:.1f}"))
            elif sig.direction == "SHORT":
                print(_r(f"▼ SHORT  score={sig.score}/100  ADX={sig.adx:.1f}"))
            else:
                print(f"◆ wait   ({sig.reason[:40]})")

            time.sleep(0.3)   # stay within IG rate limits

        # ── Display table ────────────────────────────────────────────────────
        print_signal_table(signals)

        # ── Execute trades ───────────────────────────────────────────────────
        if args.execute or args.dry_run:
            _execute_trades(
                client   = client,
                signals  = signals,
                min_score= args.exec_min_score,
                dry_run  = args.dry_run,
                log_dir  = config.OUTPUT_DIR,
            )

        # ── Save CSV ─────────────────────────────────────────────────────────
        if args.save:
            save_signals_csv(signals, config.OUTPUT_DIR)

        # ── Email alert ──────────────────────────────────────────────────────
        if not args.no_email:
            _send_signal_email(signals, equity)

    except IGAPIError as exc:
        print(_r(f"\n  IG API Error: {exc}"))
    except KeyboardInterrupt:
        print("\n  Interrupted.")
    finally:
        client.logout()


def _execute_trades(
    client:    IGClient,
    signals:   List[Signal],
    min_score: int,
    dry_run:   bool,
    log_dir:   str,
) -> None:
    active = [s for s in signals if s.direction != "WAIT" and s.score >= min_score]

    print()
    print(_b(_c("=" * 80)))
    mode = "[DRY RUN]" if dry_run else "[LIVE DEMO EXECUTION]"
    print(_b(_c(f"  {mode}  —  Executing {len(active)} signal(s)  |  min score: {min_score}/100")))
    print(_b(_c("=" * 80)))

    if not active:
        print(_y(f"\n  No signals meet the execution threshold (score ≥ {min_score}).\n"))
        return

    executor = TradeExecutor(
        client    = client,
        min_score = min_score,
        dry_run   = dry_run,
        log_dir   = log_dir,
    )

    results = executor.execute_signals(signals)

    print()
    if not results:
        print(_y("  No trades executed."))
        return

    rows = []
    for r in results:
        status_str = _g("✓ FILLED") if r.deal_status == "ACCEPTED" else \
                     (_r("✗ REJECTED") if r.deal_status == "REJECTED" else
                      _y(f"◆ {r.deal_status}"))
        rows.append([
            r.market_name[:22],
            _g(f"▲ {r.direction}") if r.direction == "LONG" else _r(f"▼ {r.direction}"),
            f"£{r.unit_size:.2f}/pt",
            f"{r.actual_level:,.4f}" if r.actual_level else "—",
            f"{r.stop_loss:,.4f}",
            f"{r.take_profit:,.4f}",
            status_str,
            r.reason[:30] if r.deal_status != "ACCEPTED" else r.deal_id[:16],
        ])

    print(tabulate(
        rows,
        headers=["Market","Dir","Size","Fill","Stop","Target","Status","Detail"],
        tablefmt="rounded_outline",
    ))
    print()
    accepted = sum(1 for r in results if r.deal_status == "ACCEPTED")
    print(f"  Summary: {accepted} filled  |  "
          f"{len(results)-accepted} rejected  |  "
          f"Log: {log_dir}/trade_log.csv")
    print()


def _send_signal_email(signals: List[Signal], equity: float) -> None:
    """Build a compact signal alert email and send it."""
    import smtplib, ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from_addr = os.getenv("EMAIL_FROM", "")
    to_raw    = os.getenv("EMAIL_TO", "")
    host      = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port      = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    user      = os.getenv("EMAIL_SMTP_USERNAME", "")
    pwd       = os.getenv("EMAIL_SMTP_PASSWORD", "")
    use_tls   = os.getenv("EMAIL_USE_TLS", "true").lower() != "false"

    if not from_addr or not to_raw or not user or not pwd:
        return

    active = [s for s in signals if s.direction != "WAIT"]
    if not active:
        subject = "MYJ Capital | Scanner — No signals today"
    else:
        dirs = ", ".join(f"{s.market_name} {s.direction}" for s in active[:3])
        subject = f"MYJ Capital | {len(active)} Signal(s): {dirs}"

    # Build HTML
    _TD = "#1B4D47"; _BG = "#0b1a18"; _ACC = "#2ab5a5"
    _POS = "#27ae60"; _NEG = "#e74c3c"; _TXT = "#f0f4f3"; _MUT = "#7aa09a"

    rows_html = ""
    for s in sorted(active, key=lambda x: -x.score):
        dc = _POS if s.direction == "LONG" else _NEG
        arrow = "▲" if s.direction == "LONG" else "▼"
        rows_html += f"""
        <tr style="background:#112320;">
          <td style="padding:10px 14px;color:{dc};font-weight:700;">{arrow} {s.market_name}</td>
          <td style="padding:10px 14px;color:{dc};font-weight:700;text-align:center;">{s.direction}</td>
          <td style="padding:10px 14px;color:{_ACC};text-align:center;">Sys {s.system}</td>
          <td style="padding:10px 14px;color:{_ACC};text-align:center;font-weight:700;">{s.score}/100</td>
          <td style="padding:10px 14px;color:{_TXT};font-family:monospace;">{s.entry_level:,.4f}</td>
          <td style="padding:10px 14px;color:{_NEG};font-family:monospace;">{s.stop_loss:,.4f}</td>
          <td style="padding:10px 14px;color:{_POS};font-family:monospace;">{s.take_profit:,.4f}</td>
          <td style="padding:10px 14px;color:{_TXT};font-family:monospace;">£{s.unit_size:.2f}/pt</td>
          <td style="padding:10px 14px;color:{_MUT};font-size:11px;">{s.reason[:50]}</td>
        </tr>"""

    no_sig = f"<p style='color:{_MUT};'>No active signals at this time.</p>" if not active else ""

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/></head>
    <body style="margin:0;padding:0;background:{_BG};font-family:Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:24px 0;">
    <tr><td align="center">
    <table width="860" cellpadding="0" cellspacing="0"
           style="background:#0d1620;border-radius:8px;border:1px solid #1e3d39;max-width:860px;">

      <tr><td style="background:linear-gradient(135deg,{_TD} 0%,#133a35 100%);padding:28px 36px;">
        <table width="100%"><tr>
          <td><span style="font-size:22px;font-weight:800;color:#fff;">MYJ</span>
              <span style="color:rgba(255,255,255,0.35);padding:0 10px;">|</span>
              <span style="font-size:14px;color:rgba(255,255,255,0.8);letter-spacing:3px;">CAPITAL</span>
              <div style="font-size:10px;color:rgba(255,255,255,0.45);letter-spacing:2px;
                          margin-top:6px;">MARKET SCANNER ALERT</div></td>
          <td align="right">
            <div style="color:rgba(255,255,255,0.5);font-size:11px;">
              {datetime.utcnow().strftime('%d %B %Y · %H:%M UTC')}<br/>
              <span style="color:#fff;font-size:13px;font-weight:600;">
                {len(active)} Active Signal(s) / {len(signals)} Markets
              </span>
            </div>
          </td>
        </tr></table>
      </td></tr>

      <tr><td style="padding:28px 36px;">
        <div style="font-size:10px;font-weight:700;color:{_ACC};letter-spacing:2px;
                    border-left:3px solid {_ACC};padding-left:10px;margin-bottom:14px;">
          ACTIVE SIGNALS
        </div>
        {no_sig}
        {"" if not active else f'''
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr style="background:{_TD};">
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;text-align:left;">Market</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Dir</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Sys</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Score</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Entry</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Stop</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Target</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Size</th>
            <th style="padding:10px 14px;color:{_TXT};font-size:10px;">Reason</th>
          </tr>
          {rows_html}
        </table>'''}

        <div style="margin-top:24px;padding:16px;background:#0a1a18;border-radius:6px;
                    border-left:3px solid #1e3d39;">
          <p style="color:{_MUT};font-size:11px;margin:0;">
            ⚠ These are signals only — not trade instructions. Each unit risks
            {DEFAULT_RISK_PCT}% of account equity (£{equity * DEFAULT_RISK_PCT / 100:,.0f}).
            Max 4 units per market. Always use stops. Past signals do not guarantee future results.
          </p>
        </div>
      </td></tr>

      <tr><td style="background:#081412;padding:18px 36px;border-top:1px solid #1e3d39;">
        <span style="font-size:12px;font-weight:700;color:{_ACC};">MYJ</span>
        <span style="font-size:12px;color:rgba(255,255,255,0.3);"> | CAPITAL · myjcapital.com</span>
      </td></tr>

    </table></td></tr></table></body></html>"""

    to_addrs = [a.strip() for a in to_raw.split(",") if a.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MYJ Capital Scanner <{from_addr}>"
    msg["To"]      = ", ".join(to_addrs)
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    try:
        if use_tls:
            with smtplib.SMTP(host, port) as s:
                s.ehlo(); s.starttls(context=ctx); s.login(user, pwd)
                s.sendmail(from_addr, to_addrs, msg.as_bytes())
        else:
            with smtplib.SMTP_SSL(host, port, context=ctx) as s:
                s.login(user, pwd); s.sendmail(from_addr, to_addrs, msg.as_bytes())
        print(_g(f"  Signal email sent → {', '.join(to_addrs)}"))
    except Exception as exc:
        print(_y(f"  Email failed: {exc}"))


if __name__ == "__main__":
    main()
