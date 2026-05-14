#!/usr/bin/env python3
"""
MYJ Capital — Real-Time Alert Monitor
======================================

Leave this running in the background. It scans all markets every hour
and emails you the MOMENT it spots a new signal.

  python alerts.py                     # Turtle + DEMA28 (both strategies)
  python alerts.py --strategy turtle   # Turtle CTA only
  python alerts.py --strategy dema     # DEMA28 multi-timeframe only
  python alerts.py --strategy both     # both (default)

Optional:
  python alerts.py --interval 30     # scan every 30 minutes
  python alerts.py --min-score 70    # only alert on strong signals
  python alerts.py --demo            # use demo account
"""

import argparse
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Set, Union

from colorama import Fore, Style, init as colorama_init

import config
from ig_client import IGClient, IGAPIError
from markets_config import MARKETS, DEFAULT_RISK_PCT
from strategy_engine import TurtleCTAStrategy, OHLC, Signal
from dema_strategy import DEMAMultiTimeframeStrategy, DEMASignal
from market_scanner import fetch_ohlc, fetch_account_equity

colorama_init(autoreset=True)
logging.basicConfig(level=logging.WARNING)

AnySignal = Union[Signal, DEMASignal]

def _g(t): return f"{Fore.GREEN}{t}{Style.RESET_ALL}"
def _r(t): return f"{Fore.RED}{t}{Style.RESET_ALL}"
def _y(t): return f"{Fore.YELLOW}{t}{Style.RESET_ALL}"
def _c(t): return f"{Fore.CYAN}{t}{Style.RESET_ALL}"
def _b(t): return f"{Style.BRIGHT}{t}{Style.RESET_ALL}"


# ── Email alert ───────────────────────────────────────────────────────────────

def send_alert(signals: List[AnySignal], equity: float) -> None:
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

    if not all([from_addr, to_raw, user, pwd]):
        print(_y("  ⚠  Email not configured — skipping (check .env)"))
        return

    to_addrs = [a.strip() for a in to_raw.split(",") if a.strip()]
    now      = datetime.utcnow().strftime("%d %b %Y · %H:%M UTC")

    parts   = [f"{'▲' if s.direction == 'LONG' else '▼'} {s.market_name}" for s in signals]
    subject = f"MYJ Capital 🚨 {len(signals)} Signal(s): {', '.join(parts[:3])}"

    # ── Brand colours ────────────────────────────────────────────────────────
    TD   = "#1B4D47"; BG   = "#0b1a18"; ACC = "#2ab5a5"
    POS  = "#27ae60"; NEG  = "#e74c3c"; TXT = "#f0f4f3"; MUT = "#7aa09a"
    CARD = "#112320"; BORDER = "#1e3d39"

    # ── Signal cards ─────────────────────────────────────────────────────────
    cards_html = ""
    for s in signals:
        dc    = POS if s.direction == "LONG" else NEG
        arrow = "▲" if s.direction == "LONG" else "▼"
        rr    = (round(abs(s.take_profit - s.entry_level) /
                       abs(s.stop_loss  - s.entry_level), 1)
                 if s.stop_loss != s.entry_level else 0)

        # Strategy badge label
        is_dema    = isinstance(s, DEMASignal)
        sys_label  = f"DEMA{s.system}" if is_dema else f"System {s.system}"
        sys_colour = "#2e6b9e" if is_dema else "#1a3530"

        # Pre-compute conditional HTML blocks (avoids nested f-string issues)
        if not is_dema:
            mom_col     = "#27ae60" if s.momentum_12m > 0 else "#e74c3c"
            adx_mom_html = (
                f'<td style="padding:0 16px;">'
                f'<span style="color:{MUT};font-size:11px;">ADX</span>'
                f'<span style="color:{TXT};font-size:12px;font-weight:700;'
                f'font-family:monospace;margin-left:6px;">{s.adx:.1f}</span>'
                f'</td>'
                f'<td style="padding:0 16px;">'
                f'<span style="color:{MUT};font-size:11px;">12m Mom</span>'
                f'<span style="color:{mom_col};font-size:12px;font-weight:700;'
                f'font-family:monospace;margin-left:6px;">{s.momentum_12m:+.1f}%</span>'
                f'</td>'
            )
        else:
            adx_mom_html = ""

        if s.pyramid_levels:
            plevels_html = "  →  ".join(
                f'<span style="color:{ACC};font-family:monospace;font-weight:700;">'
                f'{p:,.4f}</span>'
                for p in s.pyramid_levels[:4]
            )
            pyramid_html = (
                f'<div style="margin-top:10px;font-size:11px;color:{MUT};">'
                f'Add more units at: {plevels_html}'
                f'&nbsp;(0.5 ATR steps, max 4 units)</div>'
            )
        else:
            pyramid_html = ""

        # Timeframe alignment grid (DEMA only)
        tf_grid_html = ""
        if is_dema and s.tf_aligned:
            ticks = "".join(
                f'<span style="color:{"#27ae60" if ok else "#e74c3c"};'
                f'font-size:11px;margin:0 4px;">'
                f'{"✓" if ok else "✗"} {tf}</span>'
                for tf, ok in s.tf_aligned.items()
            )
            tf_grid_html = f"""
          <div style="margin:10px 0 0;padding:8px 10px;background:#0a1512;
                      border-radius:5px;font-family:monospace;">
            <span style="color:{MUT};font-size:10px;margin-right:8px;">
              Timeframes:
            </span>{ticks}
          </div>"""

        cards_html += f"""
        <div style="background:{CARD};border-radius:8px;border-left:4px solid {dc};
                    padding:20px 24px;margin-bottom:16px;">

          <table width="100%" cellpadding="0" cellspacing="0"><tr>
            <td>
              <span style="font-size:18px;font-weight:800;color:{dc};">
                {arrow} {s.market_name}
              </span>
              <span style="background:{dc};color:#fff;font-size:10px;font-weight:700;
                           border-radius:4px;padding:3px 8px;margin-left:10px;
                           letter-spacing:1px;">{s.direction}</span>
              <span style="background:{sys_colour};color:{ACC};font-size:10px;
                           font-weight:700;border-radius:4px;padding:3px 8px;
                           margin-left:6px;">{sys_label}</span>
            </td>
            <td align="right">
              <span style="font-size:13px;color:{MUT};">Score</span>
              <span style="font-size:22px;font-weight:800;color:{ACC};
                           font-family:monospace;margin-left:6px;">{s.score}</span>
              <span style="font-size:13px;color:{MUT};">/100</span>
            </td>
          </tr></table>

          <div style="color:{MUT};font-size:11px;margin:8px 0 16px;">
            {s.reason}
          </div>

          <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="text-align:center;padding:10px;background:#0d1e1c;
                       border-radius:6px;margin:2px;">
              <div style="color:{MUT};font-size:9px;text-transform:uppercase;
                          letter-spacing:1px;margin-bottom:4px;">Entry</div>
              <div style="color:{TXT};font-size:15px;font-weight:700;
                          font-family:monospace;">{s.entry_level:,.4f}</div>
            </td>
            <td style="width:6px;"></td>
            <td style="text-align:center;padding:10px;background:#0d1e1c;
                       border-radius:6px;">
              <div style="color:{MUT};font-size:9px;text-transform:uppercase;
                          letter-spacing:1px;margin-bottom:4px;">Stop Loss</div>
              <div style="color:{NEG};font-size:15px;font-weight:700;
                          font-family:monospace;">{s.stop_loss:,.4f}</div>
            </td>
            <td style="width:6px;"></td>
            <td style="text-align:center;padding:10px;background:#0d1e1c;
                       border-radius:6px;">
              <div style="color:{MUT};font-size:9px;text-transform:uppercase;
                          letter-spacing:1px;margin-bottom:4px;">Take Profit</div>
              <div style="color:{POS};font-size:15px;font-weight:700;
                          font-family:monospace;">{s.take_profit:,.4f}</div>
            </td>
            <td style="width:6px;"></td>
            <td style="text-align:center;padding:10px;background:#0d1e1c;
                       border-radius:6px;">
              <div style="color:{MUT};font-size:9px;text-transform:uppercase;
                          letter-spacing:1px;margin-bottom:4px;">R:R Ratio</div>
              <div style="color:{ACC};font-size:15px;font-weight:700;
                          font-family:monospace;">{rr}:1</div>
            </td>
          </tr>
          </table>

          {tf_grid_html}

          <table width="100%" cellpadding="0" cellspacing="0"
                 style="margin-top:12px;background:#0a1815;border-radius:6px;
                        padding:12px;">
          <tr>
            <td style="padding:0 16px;">
              <span style="color:{MUT};font-size:11px;">ATR (N)</span>
              <span style="color:{TXT};font-size:12px;font-weight:700;
                           font-family:monospace;margin-left:6px;">{s.atr:,.4f}</span>
            </td>
            <td style="padding:0 16px;">
              <span style="color:{MUT};font-size:11px;">Position size</span>
              <span style="color:{ACC};font-size:13px;font-weight:700;
                           font-family:monospace;margin-left:6px;">£{s.unit_size:.2f}/pt</span>
            </td>
            <td style="padding:0 16px;">
              <span style="color:{MUT};font-size:11px;">Risk (1 unit)</span>
              <span style="color:{NEG};font-size:13px;font-weight:700;
                           font-family:monospace;margin-left:6px;">-£{s.risk_amount:.0f}</span>
            </td>
            {adx_mom_html}
          </tr>
          </table>

          {pyramid_html}

        </div>"""

    html = f"""<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"/><title>MYJ Capital Signal Alert</title></head>
<body style="margin:0;padding:0;background:{BG};
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0"
       style="background:{BG};padding:28px 0;">
<tr><td align="center">
<table width="640" cellpadding="0" cellspacing="0"
       style="max-width:640px;width:100%;background:#0d1620;
              border-radius:10px;border:1px solid {BORDER};overflow:hidden;">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,{TD} 0%,#133a35 100%);
                 padding:28px 32px;">
    <table width="100%"><tr>
      <td>
        <div style="font-size:22px;font-weight:800;color:#fff;letter-spacing:1px;">
          MYJ<span style="color:rgba(255,255,255,0.4);padding:0 10px;
                          font-weight:300;">|</span>CAPITAL
        </div>
        <div style="font-size:10px;color:rgba(255,255,255,0.45);
                    letter-spacing:3px;margin-top:5px;">
          🚨 SIGNAL ALERT — REAL-TIME
        </div>
      </td>
      <td align="right">
        <div style="background:rgba(255,255,255,0.1);border-radius:6px;
                    padding:10px 16px;text-align:center;">
          <div style="color:rgba(255,255,255,0.6);font-size:10px;">
            {now}
          </div>
          <div style="color:#fff;font-size:18px;font-weight:800;margin-top:4px;">
            {len(signals)} New Signal{'s' if len(signals) > 1 else ''}
          </div>
        </div>
      </td>
    </tr></table>
  </td></tr>

  <!-- Body -->
  <tr><td style="padding:28px 32px;">
    {cards_html}

    <!-- Disclaimer -->
    <div style="margin-top:20px;padding:14px 18px;background:#0a1512;
                border-radius:6px;border:1px solid {BORDER};">
      <p style="color:{MUT};font-size:10px;margin:0;line-height:1.6;">
        ⚠ These are automated signals based on Turtle/CTA and DEMA28 multi-timeframe
        strategies. They are not financial advice. Each unit risks 1% of your
        account equity. Always verify the signal before trading.
        Past signals do not guarantee future results.
      </p>
    </div>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#080e0d;padding:16px 32px;
                 border-top:1px solid {BORDER};">
    <span style="color:{ACC};font-size:12px;font-weight:700;">MYJ</span>
    <span style="color:rgba(255,255,255,0.25);font-size:12px;"> | CAPITAL · myjcapital.com</span>
    <span style="float:right;color:#2a4a46;font-size:10px;">
      Real-time alert monitor
    </span>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MYJ Capital Alerts <{from_addr}>"
    msg["To"]      = ", ".join(to_addrs)
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    try:
        if use_tls:
            with smtplib.SMTP(host, port) as srv:
                srv.ehlo(); srv.starttls(context=ctx)
                srv.login(user, pwd)
                srv.sendmail(from_addr, to_addrs, msg.as_bytes())
        else:
            with smtplib.SMTP_SSL(host, port, context=ctx) as srv:
                srv.login(user, pwd)
                srv.sendmail(from_addr, to_addrs, msg.as_bytes())
        print(_g(f"  📧 Email sent → {', '.join(to_addrs)}"))
    except Exception as exc:
        print(_r(f"  ✗ Email failed: {exc}"))


# ── Scanner functions ─────────────────────────────────────────────────────────

def _alert_key(sig: AnySignal) -> str:
    """Unique key to track whether we've already alerted on this signal."""
    strategy = "DEMA" if isinstance(sig, DEMASignal) else "TURTLE"
    return f"{sig.market_name}:{sig.direction}:{strategy}:{sig.system}"


def _scan_turtle(
    client:   IGClient,
    strategy: TurtleCTAStrategy,
) -> List[Signal]:
    signals = []
    for market in MARKETS:
        bars = fetch_ohlc(client, market["epic"], days=400)
        if not bars:
            continue
        sig = strategy.analyse(bars, market)
        if sig.direction != "WAIT":
            signals.append(sig)
        time.sleep(0.3)
    return signals


def _scan_dema(
    client:   IGClient,
    strategy: DEMAMultiTimeframeStrategy,
) -> List[DEMASignal]:
    signals = []
    for market in MARKETS:
        sig = strategy.analyse(client, market)
        if sig.direction != "WAIT":
            signals.append(sig)
    return signals


def scan_once(
    client:          IGClient,
    strategy_type:   str,
    turtle_strategy: TurtleCTAStrategy,
    dema_strategy:   DEMAMultiTimeframeStrategy,
) -> List[AnySignal]:
    """Run a full scan with one or both strategies. Returns active signals only."""
    signals: List[AnySignal] = []

    if strategy_type in ("turtle", "both"):
        t_sigs = _scan_turtle(client, turtle_strategy)
        signals.extend(t_sigs)

    if strategy_type in ("dema", "both"):
        d_sigs = _scan_dema(client, dema_strategy)
        signals.extend(d_sigs)

    return signals


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(interval_minutes: int, min_score: int, demo: bool, strategy_type: str) -> None:
    base_url = config.BASE_URL_DEMO if demo else config.BASE_URL

    alerted: Set[str] = set()   # keys of signals already emailed

    strategy_label = {
        "turtle": "Turtle CTA",
        "dema":   "DEMA28 Multi-TF",
        "both":   "Turtle + DEMA28",
    }.get(strategy_type, strategy_type)

    print()
    print(_b(_c("╔══════════════════════════════════════════════════════════╗")))
    print(_b(_c("║   MYJ CAPITAL  —  REAL-TIME ALERT MONITOR               ║")))
    print(_b(_c(f"║   Strategy      : {strategy_label:<39}║")))
    print(_b(_c(f"║   Scan interval : every {interval_minutes} min                          ║")))
    print(_b(_c(f"║   Min score     : {min_score}/100                                 ║")))
    print(_b(_c(f"║   Account       : {'DEMO' if demo else 'LIVE':<8}                              ║")))
    print(_b(_c("║   Press Ctrl+C to stop                                  ║")))
    print(_b(_c("╚══════════════════════════════════════════════════════════╝")))
    print()

    while True:
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        print(f"  [{now_str}] Connecting to IG …")

        try:
            client = IGClient(base_url=base_url)
            client.login()

            equity = fetch_account_equity(client)

            turtle_strat = TurtleCTAStrategy(
                account_equity = equity,
                risk_pct       = DEFAULT_RISK_PCT / 100,
                min_score      = min_score,
            )
            dema_strat = DEMAMultiTimeframeStrategy(
                account_equity = equity,
                risk_pct       = DEFAULT_RISK_PCT / 100,
            )

            print(f"  [{now_str}] Scanning {len(MARKETS)} markets "
                  f"[{strategy_label}] …", end=" ", flush=True)
            signals = scan_once(client, strategy_type, turtle_strat, dema_strat)
            client.logout()

            # Filter by min_score
            signals = [s for s in signals if s.score >= min_score]
            print(f"  {len(signals)} signal(s) found")

            # Find new signals
            new_signals = []
            for sig in signals:
                key = _alert_key(sig)
                if key not in alerted:
                    new_signals.append(sig)
                    alerted.add(key)

            # Clear stale alerts
            active_keys = {_alert_key(s) for s in signals}
            alerted &= active_keys

            if new_signals:
                print()
                for s in new_signals:
                    arrow  = "▲" if s.direction == "LONG" else "▼"
                    col    = _g if s.direction == "LONG" else _r
                    strat  = "DEMA" if isinstance(s, DEMASignal) else "Turtle"
                    print(col(f"  🚨 [{strat}] {arrow} {s.direction} {s.market_name}") +
                          f"  score={s.score}/100  entry={s.entry_level:.4f}  "
                          f"stop={s.stop_loss:.4f}  target={s.take_profit:.4f}")
                print()
                send_alert(new_signals, equity)
            else:
                print(f"  No new signals. Next scan in {interval_minutes} min.")

        except IGAPIError as exc:
            print(_r(f"  IG API error: {exc}"))
        except Exception as exc:
            print(_r(f"  Error: {exc}"))

        # Countdown
        next_scan = interval_minutes * 60
        for remaining in range(next_scan, 0, -30):
            mins, secs = divmod(remaining, 60)
            print(f"\r  Next scan in {mins:02d}:{secs:02d} …", end="", flush=True)
            time.sleep(min(30, remaining))
        print()


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="MYJ Capital real-time alert monitor")
    p.add_argument("--interval",  type=int, default=60,
                   help="Minutes between scans (default 60)")
    p.add_argument("--min-score", type=int, default=65,
                   help="Minimum signal score to alert on (default 65)")
    p.add_argument("--strategy",  choices=["turtle", "dema", "both"], default="both",
                   help="Which strategy to run: turtle, dema, or both (default: both)")
    p.add_argument("--demo",      action="store_true",
                   help="Use IG demo account")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(
            interval_minutes = args.interval,
            min_score        = args.min_score,
            demo             = args.demo,
            strategy_type    = args.strategy,
        )
    except KeyboardInterrupt:
        print("\n\n  Monitor stopped.")
