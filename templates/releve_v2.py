"""
Modèle de relevé MYJ Capital — VERSION 2 (relevé mensuel client).

  ⚠️  Une fois publiée (premier relevé envoyé avec cette version), cette
      version devient gelée : toute évolution passe par une v3.  ⚠️

Apports par rapport à la v1 :
  - en-tête nominatif client (nom, référence de compte, période en français) ;
  - section « Historique des relevés » alimentée par l'archive des relevés
    précédents (P&L mensuel, cumul depuis l'origine, variation m/m-1) ;
  - libellés en français, mention réglementaire renforcée en pied de page.

Règle d'architecture : une version de modèle ne peut importer que des versions
antérieures DÉJÀ GELÉES (ici la v1). Ses briques de rendu ne peuvent donc plus
bouger, ce qui rend chaque relevé archivé reproductible à l'identique.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .releve_v1 import (
    _BG, _BORDER, _CARD, _NEG, _POS, _TEAL_ACCENT, _TEAL_DARK, _TEAL_DARKER,
    _TEXT_MUTED, _TEXT_PRIMARY,
    _divider, _dow_table, _fmt, _instrument_table, _kpi_row, _monthly_table,
    _pc, _pnl_stats, _recent_trades_table, _risk_stats, _section_label,
    _stat_table, _td, _th,
)

VERSION = "v2"

_MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def periode_fr(period: str) -> str:
    """'2026-07' → 'juillet 2026'."""
    try:
        y, m = period.split("-")
        return f"{_MOIS_FR[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return period


# ── Bloc client ──────────────────────────────────────────────────────────────

def _client_bar(client: Optional[Dict[str, Any]], period: str) -> str:
    if not client:
        return ""
    nom = client.get("name", "")
    ref = client.get("account_ref") or client.get("id", "")
    mandat = client.get("mandate", "")
    lignes = [
        f'<div style="font-size:20px;font-weight:700;color:{_TEXT_PRIMARY};'
        f'letter-spacing:0.3px;">{nom}</div>'
    ]
    meta = []
    if ref:
        meta.append(f"Référence compte&nbsp;: <b style=\"color:{_TEAL_ACCENT};\">{ref}</b>")
    if mandat:
        meta.append(f"Mandat&nbsp;: <b style=\"color:{_TEXT_PRIMARY};\">{mandat}</b>")
    meta.append(f"Période&nbsp;: <b style=\"color:{_TEXT_PRIMARY};\">{periode_fr(period)}</b>")
    lignes.append(
        f'<div style="font-size:12px;color:{_TEXT_MUTED};margin-top:6px;'
        f'line-height:1.9;">{"&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta)}</div>'
    )
    return (f'<div style="padding:0 0 20px;border-bottom:1px solid {_BORDER};'
            f'margin-bottom:26px;">{"".join(lignes)}</div>')


# ── Historique / comparatif ──────────────────────────────────────────────────

def _history_table(history: List[Dict[str, Any]]) -> str:
    """history = relevés précédents, du plus ancien au plus récent.

    Chaque entrée : {"period": "2026-06", "net_pnl": 1234.5, "trades": 18,
                     "win_rate": 55.0, "cumulative_pnl": 9876.5}
    """
    if not history:
        return (f'<p style="color:{_TEXT_MUTED};font-size:12px;">'
                f'Premier relevé — aucun historique antérieur.</p>')

    rows = []
    for i, h in enumerate(reversed(history[-24:])):
        net = float(h.get("net_pnl", 0))
        cum = float(h.get("cumulative_pnl", 0))
        bg = "" if i % 2 == 0 else ' background:#162d29;'
        rows.append(
            f'<tr style="{bg}">'
            + _td(periode_fr(h.get("period", "")))
            + _td(f'{int(h.get("trades", 0))}', align="right", mono=True)
            + _td(f'{float(h.get("win_rate", 0)):.1f}%', align="right", mono=True)
            + _td(_fmt(net), color=_pc(net), align="right", bold=True, mono=True)
            + _td(_fmt(cum), color=_pc(cum), align="right", mono=True)
            + "</tr>"
        )
    head = ("<tr>" + _th("Période") + _th("Trades") + _th("Taux de réussite")
            + _th("P&amp;L net") + _th("Cumul") + "</tr>")
    return (f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid {_BORDER};border-radius:6px;'
            f'overflow:hidden;">{head}{"".join(rows)}</table>')


def _comparatif(analytics: Dict[str, Any],
                history: List[Dict[str, Any]]) -> str:
    """Encart de comparaison avec le mois précédent et le cumul."""
    net = float(analytics.get("pnl_metrics", {}).get("net_pnl", 0))
    prev = float(history[-1].get("net_pnl", 0)) if history else 0.0
    cum_prev = float(history[-1].get("cumulative_pnl", 0)) if history else 0.0
    cum = cum_prev + net
    delta = net - prev

    lignes = [("P&amp;L du mois", _fmt(net), _pc(net))]
    if history:
        lignes.append((f"Mois précédent ({periode_fr(history[-1].get('period',''))})",
                       _fmt(prev), _pc(prev)))
        lignes.append(("Variation m/m-1", _fmt(delta), _pc(delta)))
    lignes.append(("Cumul depuis l'origine", _fmt(cum), _pc(cum)))
    return _stat_table(lignes)


# ── Rendu ────────────────────────────────────────────────────────────────────

def render(
    analytics: Dict[str, Any],
    accounts: Optional[List[Dict[str, Any]]] = None,
    from_date: str = "",
    to_date: str = "",
    client: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, Any]]] = None,
    period: str = "",
    generated_at: Optional[str] = None,
) -> str:
    history = history or []
    now = generated_at or datetime.utcnow().strftime("%d/%m/%Y à %H:%M UTC")
    period = period or from_date[:7]

    acct_html = ""
    if accounts:
        parts = []
        for a in accounts:
            bal = a.get("balance", {}) or {}
            b = float(bal.get("balance", 0))
            av = float(bal.get("available", 0))
            pl = float(bal.get("profitLoss", 0))
            parts.append(
                f'<span style="color:{_TEXT_MUTED};font-size:12px;margin-right:32px;">'
                f'<b style="color:{_TEXT_PRIMARY};">{a.get("accountName","Compte")}</b>'
                f'&nbsp;&nbsp;Solde <b style="color:{_TEAL_ACCENT};">'
                f'{a.get("currency","")} {b:,.2f}</b>'
                f'&nbsp;&nbsp;Disponible <b style="color:{_TEXT_PRIMARY};">{av:,.2f}</b>'
                f'&nbsp;&nbsp;P&L latent <b style="color:{_pc(pl)};">{_fmt(pl)}</b>'
                f'</span>'
            )
        acct_html = "".join(parts)

    if "error" in analytics:
        body_html = (f'{_client_bar(client, period)}'
                     f'<p style="color:{_NEG};font-size:14px;padding:20px 0;">'
                     f'{analytics["error"]}</p>')
    else:
        pm = analytics.get("pnl_metrics", {})
        ts = analytics.get("trade_statistics", {})
        sm = analytics.get("summary", {})
        rm = analytics.get("risk_metrics", {})
        dd = analytics.get("drawdown", {})

        body_html = f"""
        {_client_bar(client, period)}

        <div style="padding:0 0 20px;border-bottom:1px solid {_BORDER};
                    margin-bottom:28px;">{acct_html}</div>

        <div style="margin-bottom:32px;">{_kpi_row(analytics)}</div>

        {_divider()}

        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="50%" style="vertical-align:top;padding-right:14px;">
            {_section_label("Synthèse du mois")}
            {_comparatif(analytics, history)}
          </td>
          <td width="50%" style="vertical-align:top;padding-left:14px;">
            {_section_label("Risque &amp; Drawdown")}
            {_risk_stats(rm, dd)}
          </td>
        </tr>
        </table>

        {_divider()}

        {_section_label("Historique des relevés")}
        {_history_table(history)}

        {_divider()}

        {_section_label("Statistiques P&amp;L &amp; Trades")}
        {_pnl_stats(pm, ts, sm)}

        {_divider()}

        {_section_label("P&amp;L par instrument — Top 15")}
        {_instrument_table(analytics.get("by_instrument", []))}

        {_divider()}

        {_section_label("P&amp;L mensuel")}
        {_monthly_table(analytics.get("by_month", []))}

        {_divider()}

        {_section_label("P&amp;L par jour de la semaine")}
        {_dow_table(analytics.get("by_day_of_week", []))}

        {_divider()}

        {_section_label("Dernières opérations — 20 plus récentes")}
        {_recent_trades_table(analytics.get("recent_trades", []))}
        """

    titre = f"MYJ Capital — Relevé {periode_fr(period)}"
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{titre}</title>
</head>
<body style="margin:0;padding:0;background:{_BG};
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
             Helvetica,Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0"
       style="background:{_BG};padding:36px 0;">
<tr><td align="center">

<table width="920" cellpadding="0" cellspacing="0"
       style="max-width:920px;width:100%;background:{_CARD};
              border-radius:8px;border:1px solid {_BORDER};overflow:hidden;">

  <tr>
    <td style="background:linear-gradient(135deg,{_TEAL_DARK} 0%,{_TEAL_DARKER} 100%);
               padding:36px 44px;">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>
        <td style="vertical-align:middle;">
          <table cellpadding="0" cellspacing="0"><tr>
            <td style="font-size:26px;font-weight:800;color:#ffffff;
                       letter-spacing:1px;font-family:Georgia,serif;">MYJ</td>
            <td style="padding:0 14px;">
              <div style="width:1px;height:30px;background:rgba(255,255,255,0.35);"></div>
            </td>
            <td style="font-size:17px;font-weight:400;color:rgba(255,255,255,0.88);
                       letter-spacing:4px;text-transform:uppercase;">CAPITAL</td>
          </tr></table>
          <div style="font-size:10px;color:rgba(255,255,255,0.45);
                      letter-spacing:3px;text-transform:uppercase;
                      margin-top:8px;">Relevé de performance mensuel</div>
        </td>
        <td align="right" style="vertical-align:middle;">
          <div style="font-size:11px;color:rgba(255,255,255,0.5);
                      text-align:right;line-height:1.8;">
            <div style="color:#ffffff;font-size:13px;font-weight:600;
                        letter-spacing:0.5px;margin-bottom:4px;">
              {periode_fr(period)}
            </div>
            <div>{from_date} &nbsp;—&nbsp; {to_date}</div>
            <div>Édité le {now}</div>
          </div>
        </td>
      </tr></table>
    </td>
  </tr>

  <tr><td style="padding:36px 44px;">{body_html}</td></tr>

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
          <span style="font-size:10px;color:#2a4a46;line-height:1.7;">
            Document d'information — relevé de performance non contractuel.<br/>
            Les performances passées ne préjugent pas des performances futures.
          </span>
        </td>
      </tr></table>
    </td>
  </tr>

</table>
</td></tr>
</table>

</body>
</html>"""
