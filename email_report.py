"""
MYJ Capital — HTML email report generator and SMTP sender.

Design: matches the official MYJ Capital brand identity.
  - Header: deep teal (#1B4D47) with white MYJ | CAPITAL wordmark
  - Body: near-black (#0b1a18) with teal-card panels
  - Accents: teal (#2ab5a5) for borders & section labels
  - Positive P&L: #27ae60  |  Negative: #e74c3c
  - Fonts: system sans-serif stack (renders cleanly across all email clients)

Required .env keys
------------------
EMAIL_FROM           e.g. reports@myjcapital.com
EMAIL_TO             comma-separated recipients
EMAIL_SMTP_HOST      e.g. smtp.gmail.com
EMAIL_SMTP_PORT      587
EMAIL_SMTP_USERNAME  SMTP login
EMAIL_SMTP_PASSWORD  SMTP password / Gmail App Password
EMAIL_USE_TLS        true (default)
"""

import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

# ── Brand palette ────────────────────────────────────────────────────────────
_TEAL_DARK    = "#1B4D47"   # header / brand primary
_TEAL_DARKER  = "#133a35"   # header gradient end
_TEAL_ACCENT  = "#2ab5a5"   # section labels, borders, links
_TEAL_FAINT   = "#1a3530"   # card / row backgrounds
_TEAL_ROW_ALT = "#162d29"   # alternating table row
_BG           = "#0b1a18"   # outer background
_CARD         = "#112320"   # inner card
_TEXT_PRIMARY = "#f0f4f3"   # body text
_TEXT_MUTED   = "#7aa09a"   # labels / secondary text
_BORDER       = "#1e3d39"   # table/card borders
_POS          = "#27ae60"   # positive P&L
_NEG          = "#e74c3c"   # negative P&L
_WARN         = "#f39c12"   # warning / neutral ratio


# ── Colour helpers ───────────────────────────────────────────────────────────

def _pc(v: float) -> str:
    return _POS if v > 0 else (_NEG if v < 0 else _TEXT_PRIMARY)

def _rc(v: float) -> str:
    """Ratio colour: green ≥1.5, amber ≥0.5, red otherwise."""
    return _POS if v >= 1.5 else (_WARN if v >= 0.5 else _NEG)

def _wc(v: float) -> str:
    return _POS if v >= 50 else _NEG

def _fmt(v: float) -> str:
    return f"{v:+,.2f}"


# ── Reusable HTML atoms ──────────────────────────────────────────────────────

def _th(text: str) -> str:
    return (f'<th style="background:{_TEAL_DARK};color:{_TEXT_PRIMARY};'
            f'padding:11px 15px;font-size:10px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1.2px;'
            f'white-space:nowrap;border-bottom:2px solid {_TEAL_ACCENT};">'
            f'{text}</th>')

def _td(text: str, color: str = _TEXT_PRIMARY, align: str = "left",
        bold: bool = False, mono: bool = False) -> str:
    ff  = "font-family:monospace;" if mono else ""
    fw  = "font-weight:700;" if bold else "font-weight:400;"
    return (f'<td style="padding:10px 15px;color:{color};font-size:12px;'
            f'{fw}{ff}text-align:{align};'
            f'border-bottom:1px solid {_BORDER};">{text}</td>')

def _section_label(title: str) -> str:
    return (f'<div style="font-size:10px;font-weight:700;color:{_TEAL_ACCENT};'
            f'text-transform:uppercase;letter-spacing:2px;'
            f'border-left:3px solid {_TEAL_ACCENT};padding-left:10px;'
            f'margin-bottom:14px;">{title}</div>')

def _divider() -> str:
    return f'<div style="height:1px;background:{_BORDER};margin:28px 0;"></div>'


# ── KPI cards ────────────────────────────────────────────────────────────────

def _kpi(label: str, value: str, color: str) -> str:
    return f"""
    <td style="padding:6px;">
      <div style="background:{_TEAL_FAINT};border-radius:6px;
                  border-top:3px solid {color};
                  padding:16px 20px;min-width:130px;text-align:center;">
        <div style="color:{_TEXT_MUTED};font-size:9px;font-weight:700;
                    text-transform:uppercase;letter-spacing:1.5px;
                    margin-bottom:10px;">{label}</div>
        <div style="color:{color};font-size:20px;font-weight:700;
                    font-family:monospace;">{value}</div>
      </div>
    </td>"""

def _kpi_row(analytics: Dict[str, Any]) -> str:
    pm  = analytics.get("pnl_metrics", {})
    ts  = analytics.get("trade_statistics", {})
    rm  = analytics.get("risk_metrics", {})
    dd  = analytics.get("drawdown", {})
    net = float(pm.get("net_pnl", 0))
    wr  = float(ts.get("win_rate_pct", 0))
    pf  = float(ts.get("profit_factor", 0))
    sh  = float(rm.get("sharpe_ratio", 0))
    mdd = float(dd.get("max_drawdown_absolute", 0))
    exp = float(ts.get("expectancy", 0))

    cards = (
        _kpi("Net P&L",       _fmt(net),        _pc(net))  +
        _kpi("Win Rate",      f"{wr:.1f}%",      _wc(wr))  +
        _kpi("Profit Factor", f"{pf:.3f}",       _rc(pf))  +
        _kpi("Sharpe Ratio",  f"{sh:.3f}",       _rc(sh))  +
        _kpi("Max Drawdown",  _fmt(mdd),         _NEG)      +
        _kpi("Expectancy",    _fmt(exp),         _pc(exp))
    )
    return (f'<table cellpadding="0" cellspacing="0" style="margin:0 auto;">'
            f'<tr>{cards}</tr></table>')


# ── Stat table (key:value rows) ──────────────────────────────────────────────

def _stat_table(rows: List) -> str:
    html = f'<table width="100%" cellpadding="0" cellspacing="0">'
    for i, (label, val, color) in enumerate(rows):
        bg = _TEAL_FAINT if i % 2 == 0 else _TEAL_ROW_ALT
        html += (f'<tr style="background:{bg};">'
                 f'<td style="padding:9px 14px;color:{_TEXT_MUTED};font-size:12px;'
                 f'border-bottom:1px solid {_BORDER};">{label}</td>'
                 f'<td style="padding:9px 14px;color:{color};font-size:12px;'
                 f'font-weight:700;font-family:monospace;text-align:right;'
                 f'border-bottom:1px solid {_BORDER};">{val}</td></tr>')
    return html + '</table>'


# ── Section renderers ────────────────────────────────────────────────────────

def _pnl_stats(pm: Dict, ts: Dict, summary: Dict) -> str:
    net = float(pm.get("net_pnl", 0))
    avg = float(pm.get("average_pnl_per_trade", 0))
    exp = float(ts.get("expectancy", 0))
    wr  = float(ts.get("win_rate_pct", 0))
    pf  = float(ts.get("profit_factor", 0))
    rows = [
        ("Total Trades",          str(summary.get("total_trades", 0)),            _TEXT_PRIMARY),
        ("Winning / Losing",      f"{pm.get('winning_trades',0)} / {pm.get('losing_trades',0)}", _TEXT_PRIMARY),
        ("Breakeven",             str(pm.get("breakeven_trades", 0)),              _TEXT_MUTED),
        ("Net P&L",               _fmt(net),                                      _pc(net)),
        ("Gross Profit",          f"+{pm.get('gross_profit',0):,.2f}",            _POS),
        ("Gross Loss",            f"-{abs(pm.get('gross_loss',0)):,.2f}",         _NEG),
        ("Largest Win",           f"+{pm.get('largest_win',0):,.2f}",            _POS),
        ("Largest Loss",          f"{pm.get('largest_loss',0):,.2f}",            _NEG),
        ("Average Win",           f"+{pm.get('average_win',0):,.2f}",            _POS),
        ("Average Loss",          f"-{abs(pm.get('average_loss',0)):,.2f}",      _NEG),
        ("Avg P&L / Trade",       _fmt(avg),                                     _pc(avg)),
        ("Win Rate",              f"{wr:.2f}%",                                  _wc(wr)),
        ("Profit Factor",         f"{pf:.3f}",                                   _rc(pf)),
        ("Expectancy",            _fmt(exp),                                     _pc(exp)),
        ("Reward : Risk",         f"{ts.get('reward_risk_ratio',0):.3f}",        _TEXT_PRIMARY),
        ("Kelly Criterion",       f"{ts.get('kelly_criterion_pct',0):.2f}%",     _TEXT_PRIMARY),
        ("Max Consec. Wins",      str(ts.get("max_consecutive_wins", 0)),        _POS),
        ("Max Consec. Losses",    str(ts.get("max_consecutive_losses", 0)),      _NEG),
        ("Instruments Traded",    str(summary.get("instruments_traded", 0)),     _TEXT_PRIMARY),
        ("Period",                f"{summary.get('first_trade','')} → {summary.get('last_trade','')}", _TEXT_MUTED),
    ]
    return _stat_table(rows)


def _risk_stats(rm: Dict, dd: Dict) -> str:
    rows = [
        ("Sharpe Ratio",          f"{rm.get('sharpe_ratio',0):.3f}",            _rc(float(rm.get("sharpe_ratio",0)))),
        ("Sortino Ratio",         f"{rm.get('sortino_ratio',0):.3f}",           _rc(float(rm.get("sortino_ratio",0)))),
        ("Calmar Ratio",          f"{rm.get('calmar_ratio',0):.3f}",            _rc(float(rm.get("calmar_ratio",0)))),
        ("Annualised Return",     _fmt(float(rm.get("annualised_return",0))),   _pc(float(rm.get("annualised_return",0)))),
        ("Avg Daily P&L",         _fmt(float(rm.get("daily_pnl_mean",0))),      _pc(float(rm.get("daily_pnl_mean",0)))),
        ("Daily P&L Std Dev",     f"{rm.get('daily_pnl_std',0):,.2f}",         _TEXT_PRIMARY),
        ("Trading Days",          str(rm.get("trading_days", 0)),               _TEXT_PRIMARY),
        ("Max Drawdown (£)",      _fmt(float(dd.get("max_drawdown_absolute",0))), _NEG),
        ("Max Drawdown (%)",      f"{dd.get('max_drawdown_pct',0):.2f}%",       _NEG),
        ("Avg Drawdown",          f"{dd.get('average_drawdown',0):,.2f}",       _WARN),
        ("Longest DD (trades)",   str(dd.get("max_drawdown_duration_trades",0)), _WARN),
    ]
    return _stat_table(rows)


def _instrument_table(instruments: List[Dict]) -> str:
    if not instruments:
        return f'<p style="color:{_TEXT_MUTED};font-size:12px;">No data.</p>'
    headers = ["Instrument", "Trades", "Net P&L", "Win %", "Prof. Factor", "Avg P&L", "Best", "Worst"]
    html = (f'<table width="100%" cellpadding="0" cellspacing="0">'
            f'<tr>{"".join(_th(h) for h in headers)}</tr>')
    for i, r in enumerate(instruments[:15]):
        net = float(r.get("net_pnl", 0))
        avg = float(r.get("avg_pnl", 0))
        wr  = float(r.get("win_rate_pct", 0))
        pf  = float(r.get("profit_factor", 0))
        bg  = _TEAL_FAINT if i % 2 == 0 else _TEAL_ROW_ALT
        html += (f'<tr style="background:{bg};">'
                 + _td(str(r.get("instrument", ""))[:36])
                 + _td(str(r.get("trades", 0)), align="center")
                 + _td(_fmt(net), _pc(net), "right", bold=True, mono=True)
                 + _td(f"{wr:.1f}%", _wc(wr), "center")
                 + _td(f"{pf:.3f}", _rc(pf), "center")
                 + _td(_fmt(avg), _pc(avg), "right", mono=True)
                 + _td(f"+{r.get('largest_win',0):,.2f}", _POS, "right", mono=True)
                 + _td(f"{r.get('largest_loss',0):,.2f}", _NEG, "right", mono=True)
                 + '</tr>')
    return html + '</table>'


def _direction_table(directions: Dict) -> str:
    if not directions:
        return f'<p style="color:{_TEXT_MUTED};font-size:12px;">No data.</p>'
    headers = ["Direction", "Trades", "Net P&L", "Win %", "Prof. Factor"]
    html = (f'<table width="100%" cellpadding="0" cellspacing="0">'
            f'<tr>{"".join(_th(h) for h in headers)}</tr>')
    for i, (direction, d) in enumerate(directions.items()):
        net = float(d.get("net_pnl", 0))
        wr  = float(d.get("win_rate_pct", 0))
        pf  = float(d.get("profit_factor", 0))
        bg  = _TEAL_FAINT if i % 2 == 0 else _TEAL_ROW_ALT
        dc  = _TEAL_ACCENT if "BUY" in str(direction).upper() else _WARN
        html += (f'<tr style="background:{bg};">'
                 + _td(str(direction), dc, bold=True)
                 + _td(str(d.get("trades",0)), align="center")
                 + _td(_fmt(net), _pc(net), "right", bold=True, mono=True)
                 + _td(f"{wr:.1f}%", _wc(wr), "center")
                 + _td(f"{pf:.3f}", _rc(pf), "center")
                 + '</tr>')
    return html + '</table>'


def _monthly_table(monthly: List[Dict]) -> str:
    if not monthly:
        return f'<p style="color:{_TEXT_MUTED};font-size:12px;">No data.</p>'
    headers = ["Month", "Trades", "Net P&L", "Win %"]
    html = (f'<table width="100%" cellpadding="0" cellspacing="0">'
            f'<tr>{"".join(_th(h) for h in headers)}</tr>')
    for i, m in enumerate(monthly):
        net = float(m.get("net_pnl", 0))
        wr  = float(m.get("win_rate_pct", 0))
        bg  = _TEAL_FAINT if i % 2 == 0 else _TEAL_ROW_ALT
        html += (f'<tr style="background:{bg};">'
                 + _td(str(m.get("month","")), _TEAL_ACCENT, bold=True)
                 + _td(str(m.get("trades",0)), align="center")
                 + _td(_fmt(net), _pc(net), "right", bold=True, mono=True)
                 + _td(f"{wr:.1f}%", _wc(wr), "center")
                 + '</tr>')
    return html + '</table>'


def _dow_table(dow: List[Dict]) -> str:
    if not dow:
        return f'<p style="color:{_TEXT_MUTED};font-size:12px;">No data.</p>'
    headers = ["Day", "Trades", "Net P&L", "Win %", "Avg P&L"]
    html = (f'<table width="100%" cellpadding="0" cellspacing="0">'
            f'<tr>{"".join(_th(h) for h in headers)}</tr>')
    for i, r in enumerate(dow):
        net = float(r.get("net_pnl", 0))
        avg = float(r.get("avg_pnl", 0))
        wr  = float(r.get("win_rate_pct", 0))
        bg  = _TEAL_FAINT if i % 2 == 0 else _TEAL_ROW_ALT
        html += (f'<tr style="background:{bg};">'
                 + _td(str(r.get("day","")), _TEXT_PRIMARY)
                 + _td(str(r.get("trades",0)), align="center")
                 + _td(_fmt(net), _pc(net), "right", bold=True, mono=True)
                 + _td(f"{wr:.1f}%", _wc(wr), "center")
                 + _td(_fmt(avg), _pc(avg), "right", mono=True)
                 + '</tr>')
    return html + '</table>'


def _recent_trades_table(trades: List[Dict]) -> str:
    if not trades:
        return f'<p style="color:{_TEXT_MUTED};font-size:12px;">No trade data.</p>'
    headers = ["Date (UTC)", "Instrument", "Dir", "Size", "Open", "Close", "P&L", "Result"]
    html = (f'<table width="100%" cellpadding="0" cellspacing="0">'
            f'<tr>{"".join(_th(h) for h in headers)}</tr>')
    for i, t in enumerate(trades):
        pnl    = float(t.get("pnl", 0))
        result = str(t.get("result", ""))
        rc     = _POS if result == "WIN" else (_NEG if result == "LOSS" else _TEXT_MUTED)
        dc     = _TEAL_ACCENT if str(t.get("direction","")).upper() in ("BUY","LONG") else _WARN
        bg     = _TEAL_FAINT if i % 2 == 0 else _TEAL_ROW_ALT
        html  += (f'<tr style="background:{bg};">'
                  + _td(str(t.get("date",""))[:19], _TEXT_MUTED)
                  + _td(str(t.get("instrument",""))[:30])
                  + _td(str(t.get("direction","")), dc, "center", bold=True)
                  + _td(str(t.get("size",0)), align="center")
                  + _td(str(t.get("open_level",0)), align="right", mono=True)
                  + _td(str(t.get("close_level",0)), align="right", mono=True)
                  + _td(_fmt(pnl), _pc(pnl), "right", bold=True, mono=True)
                  + _td(result, rc, "center", bold=True)
                  + '</tr>')
    return html + '</table>'


# ── Full HTML email ──────────────────────────────────────────────────────────

def build_html_email(
    analytics: Dict[str, Any],
    accounts: Optional[List[Dict[str, Any]]] = None,
    from_date: str = "",
    to_date: str = "",
) -> str:
    now = datetime.utcnow().strftime("%d %B %Y  ·  %H:%M UTC")

    # ── Account bar ─────────────────────────────────────────────────────────
    acct_html = ""
    if accounts:
        parts = []
        for a in accounts:
            bal = a.get("balance", {})
            b   = float(bal.get("balance", 0))
            av  = float(bal.get("available", 0))
            pl  = float(bal.get("profitLoss", 0))
            parts.append(
                f'<span style="color:{_TEXT_MUTED};font-size:12px;margin-right:32px;">'
                f'<b style="color:{_TEXT_PRIMARY};">{a.get("accountName","Account")}</b>'
                f'&nbsp;&nbsp;Balance <b style="color:{_TEAL_ACCENT};">'
                f'{a.get("currency","")} {b:,.2f}</b>'
                f'&nbsp;&nbsp;Available <b style="color:{_TEXT_PRIMARY};">{av:,.2f}</b>'
                f'&nbsp;&nbsp;Open P&L <b style="color:{_pc(pl)};">{_fmt(pl)}</b>'
                f'</span>'
            )
        acct_html = "".join(parts)

    if "error" in analytics:
        body_html = (f'<p style="color:{_NEG};font-size:14px;padding:20px 0;">'
                     f'{analytics["error"]}</p>')
    else:
        sm = analytics.get("summary", {})
        pm = analytics.get("pnl_metrics", {})
        ts = analytics.get("trade_statistics", {})
        rm = analytics.get("risk_metrics", {})
        dd = analytics.get("drawdown", {})

        body_html = f"""
        <!-- Account bar -->
        <div style="padding:14px 0 20px;border-bottom:1px solid {_BORDER};
                    margin-bottom:28px;">{acct_html}</div>

        <!-- KPI row -->
        <div style="margin-bottom:32px;">{_kpi_row(analytics)}</div>

        {_divider()}

        <!-- Two-column: P&L stats | Risk metrics -->
        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="50%" style="vertical-align:top;padding-right:14px;">
            {_section_label("P&amp;L &amp; Trade Statistics")}
            {_pnl_stats(pm, ts, sm)}
          </td>
          <td width="50%" style="vertical-align:top;padding-left:14px;">
            {_section_label("Risk &amp; Drawdown Metrics")}
            {_risk_stats(rm, dd)}
          </td>
        </tr>
        </table>

        {_divider()}

        <!-- Instrument breakdown -->
        {_section_label("P&amp;L by Instrument — Top 15")}
        {_instrument_table(analytics.get("by_instrument", []))}

        {_divider()}

        <!-- Direction + Monthly -->
        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="32%" style="vertical-align:top;padding-right:14px;">
            {_section_label("Long vs Short")}
            {_direction_table(analytics.get("by_direction", {}))}
          </td>
          <td width="68%" style="vertical-align:top;padding-left:14px;">
            {_section_label("Monthly P&amp;L")}
            {_monthly_table(analytics.get("by_month", []))}
          </td>
        </tr>
        </table>

        {_divider()}

        <!-- Day of week -->
        {_section_label("P&amp;L by Day of Week")}
        {_dow_table(analytics.get("by_day_of_week", []))}

        {_divider()}

        <!-- Recent trades -->
        {_section_label("Recent Trades — Last 20")}
        {_recent_trades_table(analytics.get("recent_trades", []))}
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>MYJ Capital — Trading Analytics</title>
</head>
<body style="margin:0;padding:0;background:{_BG};
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
             Helvetica,Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0"
       style="background:{_BG};padding:36px 0;">
<tr><td align="center">

<!-- ── Email card ── -->
<table width="920" cellpadding="0" cellspacing="0"
       style="max-width:920px;width:100%;background:{_CARD};
              border-radius:8px;border:1px solid {_BORDER};
              overflow:hidden;">

  <!-- ── HEADER ── -->
  <tr>
    <td style="background:linear-gradient(135deg,{_TEAL_DARK} 0%,{_TEAL_DARKER} 100%);
               padding:36px 44px;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>

        <!-- Logo -->
        <td style="vertical-align:middle;">
          <table cellpadding="0" cellspacing="0"><tr>
            <td style="font-size:26px;font-weight:800;color:#ffffff;
                       letter-spacing:1px;font-family:Georgia,serif;">
              MYJ
            </td>
            <td style="padding:0 14px;">
              <div style="width:1px;height:30px;background:rgba(255,255,255,0.35);"></div>
            </td>
            <td style="font-size:17px;font-weight:400;color:rgba(255,255,255,0.88);
                       letter-spacing:4px;text-transform:uppercase;">
              CAPITAL
            </td>
          </tr></table>
          <div style="font-size:10px;color:rgba(255,255,255,0.45);
                      letter-spacing:3px;text-transform:uppercase;
                      margin-top:8px;">
            Performance Analytics Report
          </div>
        </td>

        <!-- Period + date -->
        <td align="right" style="vertical-align:middle;">
          <div style="font-size:11px;color:rgba(255,255,255,0.5);
                      text-align:right;line-height:1.8;">
            <div style="color:#ffffff;font-size:13px;font-weight:600;
                        letter-spacing:0.5px;margin-bottom:4px;">
              {from_date} &nbsp;—&nbsp; {to_date}
            </div>
            <div>{now}</div>
          </div>
        </td>

      </tr></table>
    </td>
  </tr>

  <!-- ── BODY ── -->
  <tr>
    <td style="padding:36px 44px;">
      {body_html}
    </td>
  </tr>

  <!-- ── FOOTER ── -->
  <tr>
    <td style="background:#081412;padding:22px 44px;
               border-top:1px solid {_BORDER};">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td>
          <span style="font-size:13px;font-weight:700;color:{_TEAL_ACCENT};
                       letter-spacing:1px;">MYJ</span>
          <span style="font-size:13px;color:rgba(255,255,255,0.4);
                       letter-spacing:1px;"> | CAPITAL</span>
          <span style="font-size:11px;color:#3a6660;margin-left:16px;">
            myjcapital.com
          </span>
        </td>
        <td align="right">
          <span style="font-size:10px;color:#2a4a46;">
            Past performance is not indicative of future results.
            For informational purposes only.
          </span>
        </td>
      </tr></table>
    </td>
  </tr>

</table><!-- /card -->
</td></tr>
</table><!-- /outer -->

</body>
</html>"""


# ── SMTP sender ──────────────────────────────────────────────────────────────

def send_email_report(
    html: str,
    analytics: Dict[str, Any],
    from_date: str = "",
    to_date: str = "",
) -> None:
    from_addr = os.getenv("EMAIL_FROM", "")
    to_raw    = os.getenv("EMAIL_TO", "")
    host      = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port      = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    user      = os.getenv("EMAIL_SMTP_USERNAME", "")
    pwd       = os.getenv("EMAIL_SMTP_PASSWORD", "")
    use_tls   = os.getenv("EMAIL_USE_TLS", "true").lower() != "false"

    if not from_addr or not to_raw:
        print("  Email skipped — EMAIL_FROM / EMAIL_TO not set in .env")
        return
    if not user or not pwd:
        print("  Email skipped — SMTP credentials not set in .env")
        return

    to_addrs = [a.strip() for a in to_raw.split(",") if a.strip()]
    pm  = analytics.get("pnl_metrics", {})
    net = float(pm.get("net_pnl", 0))
    sgn = "+" if net >= 0 else ""
    subject = (f"MYJ Capital | Analytics {from_date} → {to_date} | "
               f"P&L {sgn}{net:,.2f}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MYJ Capital <{from_addr}>"
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
                s.login(user, pwd)
                s.sendmail(from_addr, to_addrs, msg.as_bytes())
        print(f"  Email sent → {', '.join(to_addrs)}")
    except Exception as exc:
        print(f"  Email failed: {exc}")
