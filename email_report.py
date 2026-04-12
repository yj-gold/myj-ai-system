"""
MYJ Capital — HTML email report generator and SMTP sender.

Builds a fully styled HTML email from the analytics dict and sends it
via any SMTP server (Gmail, Outlook, custom).

Required .env keys
------------------
EMAIL_FROM          e.g. reports@myjcapital.com
EMAIL_TO            comma-separated list of recipients
EMAIL_SMTP_HOST     e.g. smtp.gmail.com
EMAIL_SMTP_PORT     587
EMAIL_SMTP_USERNAME your SMTP login
EMAIL_SMTP_PASSWORD your SMTP password (Gmail: use an App Password)
EMAIL_USE_TLS       true  (default)
"""

import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Colour helpers (HTML)
# ---------------------------------------------------------------------------

def _pnl_color(value: float) -> str:
    return "#00c853" if value > 0 else ("#ff1744" if value < 0 else "#e0e0e0")


def _pnl_str(value: float) -> str:
    return f"{value:+,.2f}"


def _pct_color(value: float) -> str:
    return "#00c853" if value >= 50 else "#ff1744"


def _ratio_color(value: float) -> str:
    if value >= 1.5:
        return "#00c853"
    if value >= 0.5:
        return "#ffd600"
    return "#ff1744"


# ---------------------------------------------------------------------------
# HTML building blocks
# ---------------------------------------------------------------------------

def _kpi_card(label: str, value: str, color: str = "#e0e0e0") -> str:
    return f"""
    <td style="padding:8px;">
      <div style="background:#1e2a3a;border-radius:8px;padding:18px 22px;
                  min-width:140px;text-align:center;border-top:3px solid {color};">
        <div style="color:#7b8fa6;font-size:11px;text-transform:uppercase;
                    letter-spacing:1px;margin-bottom:8px;">{label}</div>
        <div style="color:{color};font-size:22px;font-weight:700;
                    font-family:monospace;">{value}</div>
      </div>
    </td>"""


def _section_header(title: str) -> str:
    return f"""
    <tr><td colspan="99" style="padding:28px 0 6px 0;">
      <div style="border-left:4px solid #1565c0;padding-left:12px;">
        <span style="color:#90caf9;font-size:13px;font-weight:700;
                     text-transform:uppercase;letter-spacing:1.5px;">{title}</span>
      </div>
    </td></tr>"""


def _th(text: str) -> str:
    return (f'<th style="background:#1565c0;color:#e3f2fd;padding:10px 14px;'
            f'font-size:11px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.8px;white-space:nowrap;">{text}</th>')


def _td(text: str, color: str = "#cfd8dc", align: str = "left",
        bold: bool = False) -> str:
    weight = "700" if bold else "400"
    return (f'<td style="padding:9px 14px;color:{color};font-size:12px;'
            f'font-weight:{weight};text-align:{align};'
            f'border-bottom:1px solid #1a2535;">{text}</td>')


def _row_open(even: bool) -> str:
    bg = "#111d2b" if even else "#0d1620"
    return f'<tr style="background:{bg};">'


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_kpi_row(analytics: Dict[str, Any]) -> str:
    pm = analytics.get("pnl_metrics", {})
    ts = analytics.get("trade_statistics", {})
    rm = analytics.get("risk_metrics", {})
    dd = analytics.get("drawdown", {})

    net = float(pm.get("net_pnl", 0))
    wr  = float(ts.get("win_rate_pct", 0))
    pf  = float(ts.get("profit_factor", 0))
    sh  = float(rm.get("sharpe_ratio", 0))
    mdd = float(dd.get("max_drawdown_absolute", 0))
    exp = float(ts.get("expectancy", 0))

    cards = (
        _kpi_card("Net P&L", _pnl_str(net), _pnl_color(net)) +
        _kpi_card("Win Rate", f"{wr:.1f}%", _pct_color(wr)) +
        _kpi_card("Profit Factor", f"{pf:.3f}", _ratio_color(pf)) +
        _kpi_card("Sharpe Ratio", f"{sh:.3f}", _ratio_color(sh)) +
        _kpi_card("Max Drawdown", _pnl_str(mdd), "#ff1744") +
        _kpi_card("Expectancy", _pnl_str(exp), _pnl_color(exp))
    )
    return f"""
    <tr><td>
      <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
        <tr>{cards}</tr>
      </table>
    </td></tr>"""


def _render_pnl_table(pm: Dict[str, Any], ts: Dict[str, Any],
                      summary: Dict[str, Any]) -> str:
    net = float(pm.get("net_pnl", 0))
    rows = [
        ("Total Trades",          str(summary.get("total_trades", 0)),         "#e0e0e0"),
        ("Winning Trades",        str(pm.get("winning_trades", 0)),             "#00c853"),
        ("Losing Trades",         str(pm.get("losing_trades", 0)),              "#ff1744"),
        ("Breakeven Trades",      str(pm.get("breakeven_trades", 0)),           "#e0e0e0"),
        ("Net P&L",               _pnl_str(net),                               _pnl_color(net)),
        ("Gross Profit",          f"+{pm.get('gross_profit',0):,.2f}",          "#00c853"),
        ("Gross Loss",            f"-{abs(pm.get('gross_loss',0)):,.2f}",       "#ff1744"),
        ("Largest Win",           f"+{pm.get('largest_win',0):,.2f}",           "#00c853"),
        ("Largest Loss",          f"{pm.get('largest_loss',0):,.2f}",           "#ff1744"),
        ("Average Win",           f"+{pm.get('average_win',0):,.2f}",           "#00c853"),
        ("Average Loss",          f"-{abs(pm.get('average_loss',0)):,.2f}",     "#ff1744"),
        ("Average P&L / Trade",   _pnl_str(float(pm.get("average_pnl_per_trade",0))),
                                                                                _pnl_color(float(pm.get("average_pnl_per_trade",0)))),
        ("Win Rate",              f"{ts.get('win_rate_pct',0):.2f}%",           _pct_color(float(ts.get("win_rate_pct",0)))),
        ("Profit Factor",         f"{ts.get('profit_factor',0):.3f}",          _ratio_color(float(ts.get("profit_factor",0)))),
        ("Expectancy / Trade",    _pnl_str(float(ts.get("expectancy",0))),     _pnl_color(float(ts.get("expectancy",0)))),
        ("Reward : Risk Ratio",   f"{ts.get('reward_risk_ratio',0):.3f}",      "#e0e0e0"),
        ("Kelly Criterion",       f"{ts.get('kelly_criterion_pct',0):.2f}%",   "#e0e0e0"),
        ("Max Consecutive Wins",  str(ts.get("max_consecutive_wins",0)),        "#00c853"),
        ("Max Consecutive Losses",str(ts.get("max_consecutive_losses",0)),      "#ff1744"),
        ("Instruments Traded",    str(summary.get("instruments_traded",0)),    "#e0e0e0"),
        ("Period",                f"{summary.get('first_trade','')} → {summary.get('last_trade','')}",
                                                                                "#7b8fa6"),
    ]
    html = '<table width="100%" cellpadding="0" cellspacing="0">'
    for i, (label, val, color) in enumerate(rows):
        bg = "#111d2b" if i % 2 == 0 else "#0d1620"
        html += (f'<tr style="background:{bg};">'
                 f'<td style="padding:9px 14px;color:#7b8fa6;font-size:12px;'
                 f'border-bottom:1px solid #1a2535;">{label}</td>'
                 f'<td style="padding:9px 14px;color:{color};font-size:12px;'
                 f'font-weight:700;text-align:right;font-family:monospace;'
                 f'border-bottom:1px solid #1a2535;">{val}</td></tr>')
    html += '</table>'
    return html


def _render_risk_table(rm: Dict[str, Any], dd: Dict[str, Any]) -> str:
    rows = [
        ("Sharpe Ratio (annualised)",   f"{rm.get('sharpe_ratio',0):.3f}",      _ratio_color(float(rm.get("sharpe_ratio",0)))),
        ("Sortino Ratio (annualised)",  f"{rm.get('sortino_ratio',0):.3f}",     _ratio_color(float(rm.get("sortino_ratio",0)))),
        ("Calmar Ratio",                f"{rm.get('calmar_ratio',0):.3f}",      _ratio_color(float(rm.get("calmar_ratio",0)))),
        ("Annualised Return",           _pnl_str(float(rm.get("annualised_return",0))),
                                                                                 _pnl_color(float(rm.get("annualised_return",0)))),
        ("Avg Daily P&L",               _pnl_str(float(rm.get("daily_pnl_mean",0))),
                                                                                 _pnl_color(float(rm.get("daily_pnl_mean",0)))),
        ("Daily P&L Std Dev",           f"{rm.get('daily_pnl_std',0):,.2f}",   "#e0e0e0"),
        ("Trading Days",                str(rm.get("trading_days",0)),           "#e0e0e0"),
        ("Max Drawdown (absolute)",     _pnl_str(float(dd.get("max_drawdown_absolute",0))), "#ff1744"),
        ("Max Drawdown (%)",            f"{dd.get('max_drawdown_pct',0):.2f}%", "#ff1744"),
        ("Average Drawdown",            f"{dd.get('average_drawdown',0):,.2f}", "#ff9100"),
        ("Longest DD Streak (trades)",  str(dd.get("max_drawdown_duration_trades",0)), "#ff9100"),
    ]
    html = '<table width="100%" cellpadding="0" cellspacing="0">'
    for i, (label, val, color) in enumerate(rows):
        bg = "#111d2b" if i % 2 == 0 else "#0d1620"
        html += (f'<tr style="background:{bg};">'
                 f'<td style="padding:9px 14px;color:#7b8fa6;font-size:12px;'
                 f'border-bottom:1px solid #1a2535;">{label}</td>'
                 f'<td style="padding:9px 14px;color:{color};font-size:12px;'
                 f'font-weight:700;text-align:right;font-family:monospace;'
                 f'border-bottom:1px solid #1a2535;">{val}</td></tr>')
    html += '</table>'
    return html


def _render_instrument_table(instruments: List[Dict[str, Any]]) -> str:
    if not instruments:
        return '<p style="color:#7b8fa6;font-size:12px;">No data.</p>'
    headers = ["Instrument", "Trades", "Net P&L", "Win %", "Prof. Factor", "Avg P&L", "Best", "Worst"]
    html = ('<table width="100%" cellpadding="0" cellspacing="0">'
            '<tr>' + ''.join(_th(h) for h in headers) + '</tr>')
    for i, r in enumerate(instruments[:15]):
        net = float(r.get("net_pnl", 0))
        avg = float(r.get("avg_pnl", 0))
        wr  = float(r.get("win_rate_pct", 0))
        pf  = float(r.get("profit_factor", 0))
        bg  = "#111d2b" if i % 2 == 0 else "#0d1620"
        html += (f'<tr style="background:{bg};">'
                 + _td(str(r.get("instrument",""))[:38])
                 + _td(str(r.get("trades",0)), align="center")
                 + _td(_pnl_str(net), color=_pnl_color(net), align="right", bold=True)
                 + _td(f"{wr:.1f}%", color=_pct_color(wr), align="center")
                 + _td(f"{pf:.3f}", color=_ratio_color(pf), align="center")
                 + _td(_pnl_str(avg), color=_pnl_color(avg), align="right")
                 + _td(f"+{r.get('largest_win',0):,.2f}", color="#00c853", align="right")
                 + _td(f"{r.get('largest_loss',0):,.2f}", color="#ff1744", align="right")
                 + '</tr>')
    html += '</table>'
    return html


def _render_direction_table(directions: Dict[str, Any]) -> str:
    if not directions:
        return '<p style="color:#7b8fa6;font-size:12px;">No data.</p>'
    headers = ["Direction", "Trades", "Net P&L", "Win %", "Profit Factor"]
    html = ('<table width="100%" cellpadding="0" cellspacing="0">'
            '<tr>' + ''.join(_th(h) for h in headers) + '</tr>')
    for i, (direction, d) in enumerate(directions.items()):
        net = float(d.get("net_pnl", 0))
        wr  = float(d.get("win_rate_pct", 0))
        pf  = float(d.get("profit_factor", 0))
        bg  = "#111d2b" if i % 2 == 0 else "#0d1620"
        dir_color = "#42a5f5" if "BUY" in str(direction).upper() else "#ef9a9a"
        html += (f'<tr style="background:{bg};">'
                 + _td(str(direction), color=dir_color, bold=True)
                 + _td(str(d.get("trades",0)), align="center")
                 + _td(_pnl_str(net), color=_pnl_color(net), align="right", bold=True)
                 + _td(f"{wr:.1f}%", color=_pct_color(wr), align="center")
                 + _td(f"{pf:.3f}", color=_ratio_color(pf), align="center")
                 + '</tr>')
    html += '</table>'
    return html


def _render_monthly_table(monthly: List[Dict[str, Any]]) -> str:
    if not monthly:
        return '<p style="color:#7b8fa6;font-size:12px;">No data.</p>'
    headers = ["Month", "Trades", "Net P&L", "Win %"]
    html = ('<table width="100%" cellpadding="0" cellspacing="0">'
            '<tr>' + ''.join(_th(h) for h in headers) + '</tr>')
    for i, m in enumerate(monthly):
        net = float(m.get("net_pnl", 0))
        wr  = float(m.get("win_rate_pct", 0))
        bg  = "#111d2b" if i % 2 == 0 else "#0d1620"
        html += (f'<tr style="background:{bg};">'
                 + _td(str(m.get("month","")), color="#90caf9", bold=True)
                 + _td(str(m.get("trades",0)), align="center")
                 + _td(_pnl_str(net), color=_pnl_color(net), align="right", bold=True)
                 + _td(f"{wr:.1f}%", color=_pct_color(wr), align="center")
                 + '</tr>')
    html += '</table>'
    return html


def _render_recent_trades(trades: List[Dict[str, Any]]) -> str:
    if not trades:
        return '<p style="color:#7b8fa6;font-size:12px;">No trade data.</p>'
    headers = ["Date (UTC)", "Instrument", "Dir", "Size", "Open", "Close", "P&L", "Result"]
    html = ('<table width="100%" cellpadding="0" cellspacing="0">'
            '<tr>' + ''.join(_th(h) for h in headers) + '</tr>')
    for i, t in enumerate(trades):
        pnl    = float(t.get("pnl", 0))
        result = str(t.get("result", ""))
        res_color = "#00c853" if result == "WIN" else ("#ff1744" if result == "LOSS" else "#e0e0e0")
        dir_color = "#42a5f5" if str(t.get("direction","")).upper() in ("BUY","LONG") else "#ef9a9a"
        bg = "#111d2b" if i % 2 == 0 else "#0d1620"
        html += (f'<tr style="background:{bg};">'
                 + _td(str(t.get("date",""))[:19], color="#7b8fa6")
                 + _td(str(t.get("instrument",""))[:32])
                 + _td(str(t.get("direction","")), color=dir_color, bold=True, align="center")
                 + _td(str(t.get("size",0)), align="center")
                 + _td(str(t.get("open_level",0)), align="right")
                 + _td(str(t.get("close_level",0)), align="right")
                 + _td(_pnl_str(pnl), color=_pnl_color(pnl), align="right", bold=True)
                 + _td(result, color=res_color, align="center", bold=True)
                 + '</tr>')
    html += '</table>'
    return html


def _render_dow_table(dow: List[Dict[str, Any]]) -> str:
    if not dow:
        return '<p style="color:#7b8fa6;font-size:12px;">No data.</p>'
    headers = ["Day", "Trades", "Net P&L", "Win %", "Avg P&L"]
    html = ('<table width="100%" cellpadding="0" cellspacing="0">'
            '<tr>' + ''.join(_th(h) for h in headers) + '</tr>')
    for i, r in enumerate(dow):
        net = float(r.get("net_pnl", 0))
        avg = float(r.get("avg_pnl", 0))
        wr  = float(r.get("win_rate_pct", 0))
        bg  = "#111d2b" if i % 2 == 0 else "#0d1620"
        html += (f'<tr style="background:{bg};">'
                 + _td(str(r.get("day","")), color="#90caf9")
                 + _td(str(r.get("trades",0)), align="center")
                 + _td(_pnl_str(net), color=_pnl_color(net), align="right", bold=True)
                 + _td(f"{wr:.1f}%", color=_pct_color(wr), align="center")
                 + _td(_pnl_str(avg), color=_pnl_color(avg), align="right")
                 + '</tr>')
    html += '</table>'
    return html


# ---------------------------------------------------------------------------
# Full HTML builder
# ---------------------------------------------------------------------------

def build_html_email(
    analytics: Dict[str, Any],
    accounts: Optional[List[Dict[str, Any]]] = None,
    from_date: str = "",
    to_date: str = "",
) -> str:
    now = datetime.utcnow().strftime("%d %B %Y — %H:%M UTC")

    if "error" in analytics:
        body = f'<p style="color:#ff1744;font-size:14px;">{analytics["error"]}</p>'
    else:
        summary    = analytics.get("summary", {})
        pm         = analytics.get("pnl_metrics", {})
        ts         = analytics.get("trade_statistics", {})
        rm         = analytics.get("risk_metrics", {})
        dd         = analytics.get("drawdown", {})
        instruments= analytics.get("by_instrument", [])
        directions = analytics.get("by_direction", {})
        monthly    = analytics.get("by_month", [])
        dow        = analytics.get("by_day_of_week", [])
        trades     = analytics.get("recent_trades", [])

        # Account summary line
        acct_html = ""
        if accounts:
            for a in accounts:
                bal = a.get("balance", {})
                acct_html += (
                    f'<span style="color:#90caf9;font-size:12px;margin-right:24px;">'
                    f'<b style="color:#e0e0e0;">{a.get("accountName","Account")}</b>'
                    f' &nbsp;|&nbsp; Balance: '
                    f'<b style="color:#00c853;">{a.get("currency","")} '
                    f'{float(bal.get("balance",0)):,.2f}</b>'
                    f' &nbsp;|&nbsp; Available: '
                    f'<b>{float(bal.get("available",0)):,.2f}</b></span>'
                )

        body = f"""
        <!-- Account bar -->
        <tr><td style="padding:10px 0 20px 0;border-bottom:1px solid #1e2a3a;">
          {acct_html}
        </td></tr>

        <!-- KPI cards -->
        {_render_kpi_row(analytics)}

        <!-- P&L + Trade Statistics -->
        <tr><td style="padding-top:32px;">
          <table width="100%" cellpadding="0" cellspacing="0"><tr>
            <td width="50%" style="vertical-align:top;padding-right:12px;">
              <div style="color:#90caf9;font-size:11px;font-weight:700;
                          text-transform:uppercase;letter-spacing:1.5px;
                          border-left:4px solid #1565c0;padding-left:10px;
                          margin-bottom:12px;">P&L &amp; Trade Statistics</div>
              {_render_pnl_table(pm, ts, summary)}
            </td>
            <td width="50%" style="vertical-align:top;padding-left:12px;">
              <div style="color:#90caf9;font-size:11px;font-weight:700;
                          text-transform:uppercase;letter-spacing:1.5px;
                          border-left:4px solid #1565c0;padding-left:10px;
                          margin-bottom:12px;">Risk &amp; Drawdown Metrics</div>
              {_render_risk_table(rm, dd)}
            </td>
          </tr></table>
        </td></tr>

        <!-- By Instrument -->
        <tr><td style="padding-top:32px;">
          <div style="color:#90caf9;font-size:11px;font-weight:700;
                      text-transform:uppercase;letter-spacing:1.5px;
                      border-left:4px solid #1565c0;padding-left:10px;
                      margin-bottom:12px;">P&L by Instrument (Top 15)</div>
          {_render_instrument_table(instruments)}
        </td></tr>

        <!-- Direction + Monthly side by side -->
        <tr><td style="padding-top:32px;">
          <table width="100%" cellpadding="0" cellspacing="0"><tr>
            <td width="35%" style="vertical-align:top;padding-right:12px;">
              <div style="color:#90caf9;font-size:11px;font-weight:700;
                          text-transform:uppercase;letter-spacing:1.5px;
                          border-left:4px solid #1565c0;padding-left:10px;
                          margin-bottom:12px;">Long vs Short</div>
              {_render_direction_table(directions)}
            </td>
            <td width="65%" style="vertical-align:top;padding-left:12px;">
              <div style="color:#90caf9;font-size:11px;font-weight:700;
                          text-transform:uppercase;letter-spacing:1.5px;
                          border-left:4px solid #1565c0;padding-left:10px;
                          margin-bottom:12px;">Monthly P&L</div>
              {_render_monthly_table(monthly)}
            </td>
          </tr></table>
        </td></tr>

        <!-- Day of week -->
        <tr><td style="padding-top:32px;">
          <div style="color:#90caf9;font-size:11px;font-weight:700;
                      text-transform:uppercase;letter-spacing:1.5px;
                      border-left:4px solid #1565c0;padding-left:10px;
                      margin-bottom:12px;">P&L by Day of Week</div>
          {_render_dow_table(dow)}
        </td></tr>

        <!-- Recent trades -->
        <tr><td style="padding-top:32px;">
          <div style="color:#90caf9;font-size:11px;font-weight:700;
                      text-transform:uppercase;letter-spacing:1.5px;
                      border-left:4px solid #1565c0;padding-left:10px;
                      margin-bottom:12px;">Recent Trades (Last 20)</div>
          {_render_recent_trades(trades)}
        </td></tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>MYJ Capital — Trading Analytics Report</title>
</head>
<body style="margin:0;padding:0;background:#0a0f18;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">

  <!-- Outer wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#0a0f18;padding:30px 0;">
  <tr><td align="center">

  <!-- Email card -->
  <table width="900" cellpadding="0" cellspacing="0"
         style="background:#0d1620;border-radius:12px;
                border:1px solid #1e2a3a;overflow:hidden;
                max-width:900px;width:100%;">

    <!-- ── HEADER ── -->
    <tr>
      <td style="background:linear-gradient(135deg,#0d1b3e 0%,#1565c0 100%);
                 padding:36px 40px;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td>
            <!-- Logo / brand -->
            <div style="font-size:28px;font-weight:900;color:#ffffff;
                        letter-spacing:3px;font-family:Georgia,serif;">
              MYJ<span style="color:#42a5f5;"> CAPITAL</span>
            </div>
            <div style="font-size:11px;color:#90caf9;letter-spacing:4px;
                        text-transform:uppercase;margin-top:4px;">
              Trading Analytics Report
            </div>
          </td>
          <td align="right">
            <div style="color:#90caf9;font-size:11px;text-align:right;">
              <div style="color:#ffffff;font-size:13px;font-weight:600;
                          margin-bottom:4px;">Period Analysed</div>
              <div>{from_date} &nbsp;→&nbsp; {to_date}</div>
              <div style="margin-top:6px;color:#7b8fa6;">{now}</div>
            </div>
          </td>
        </tr></table>
      </td>
    </tr>

    <!-- ── BODY ── -->
    <tr><td style="padding:28px 40px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        {body}
      </table>
    </td></tr>

    <!-- ── FOOTER ── -->
    <tr>
      <td style="background:#080d14;padding:24px 40px;
                 border-top:1px solid #1e2a3a;">
        <table width="100%" cellpadding="0" cellspacing="0"><tr>
          <td>
            <div style="color:#7b8fa6;font-size:11px;">
              <b style="color:#42a5f5;letter-spacing:2px;">MYJ CAPITAL</b>
              &nbsp;·&nbsp; myjcapital.com
            </div>
            <div style="color:#3d5166;font-size:10px;margin-top:6px;">
              This report is generated automatically from your IG Markets account
              data and is for informational purposes only. Past performance is not
              indicative of future results.
            </div>
          </td>
          <td align="right" style="vertical-align:top;">
            <div style="color:#3d5166;font-size:10px;">
              Powered by MYJ Analytics Engine
            </div>
          </td>
        </tr></table>
      </td>
    </tr>

  </table><!-- /email card -->
  </td></tr>
  </table><!-- /outer -->

</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# SMTP sender
# ---------------------------------------------------------------------------

def send_email_report(
    html: str,
    analytics: Dict[str, Any],
    from_date: str = "",
    to_date: str = "",
) -> None:
    """Send the HTML report via SMTP. Reads config from environment."""
    from_addr  = os.getenv("EMAIL_FROM", "")
    to_raw     = os.getenv("EMAIL_TO", "")
    smtp_host  = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    smtp_port  = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    smtp_user  = os.getenv("EMAIL_SMTP_USERNAME", "")
    smtp_pass  = os.getenv("EMAIL_SMTP_PASSWORD", "")
    use_tls    = os.getenv("EMAIL_USE_TLS", "true").lower() != "false"

    if not from_addr or not to_raw:
        print("  Email skipped — EMAIL_FROM / EMAIL_TO not configured in .env")
        return
    if not smtp_user or not smtp_pass:
        print("  Email skipped — SMTP credentials not configured in .env")
        return

    to_addrs = [a.strip() for a in to_raw.split(",") if a.strip()]

    pm  = analytics.get("pnl_metrics", {})
    net = float(pm.get("net_pnl", 0))
    sign = "+" if net >= 0 else ""
    subject = (
        f"MYJ Capital | Trading Report {from_date} → {to_date} | "
        f"P&L: {sign}{net:,.2f}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MYJ Capital Reports <{from_addr}>"
    msg["To"]      = ", ".join(to_addrs)
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    try:
        if use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, to_addrs, msg.as_bytes())
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, to_addrs, msg.as_bytes())
        print(f"  Email sent → {', '.join(to_addrs)}")
    except Exception as exc:
        print(f"  Email failed: {exc}")
