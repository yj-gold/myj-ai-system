"""
MYJ Capital — envoi SMTP des relevés.

Le rendu HTML n'est plus défini ici : il vit dans `templates/`, où chaque
version du modèle est gelée et archivée (voir docs/RELEVES.md). Ce module ne
garde que le transport e-mail, plus un ré-export de `build_html_email` pour
que les scripts existants (main.py, preview.py) continuent de fonctionner.

Clés .env requises
------------------
EMAIL_FROM           ex. reports@myjcapital.com
EMAIL_TO             destinataires séparés par des virgules
EMAIL_SMTP_HOST      ex. smtp.gmail.com
EMAIL_SMTP_PORT      587
EMAIL_SMTP_USERNAME  identifiant SMTP
EMAIL_SMTP_PASSWORD  mot de passe SMTP / App Password Gmail
EMAIL_USE_TLS        true (défaut)
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

# Modèle historique (v1) — conservé comme rendu par défaut de main.py/preview.py
from templates.releve_v1 import build_html_email  # noqa: F401  (ré-export)

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


# ── Envoi ciblé (relevés clients) ────────────────────────────────────────────

def smtp_settings() -> Dict[str, Any]:
    """Paramètres SMTP lus dans l'environnement."""
    return {
        "from_addr": os.getenv("EMAIL_FROM", ""),
        "host": os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
        "user": os.getenv("EMAIL_SMTP_USERNAME", ""),
        "pwd": os.getenv("EMAIL_SMTP_PASSWORD", ""),
        "use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() != "false",
    }


def send_html(html: str, subject: str, to_addrs: List[str],
              reply_to: Optional[str] = None) -> str:
    """Envoie un HTML à des destinataires explicites.

    Retourne un statut : "sent", "skipped:<raison>" ou "failed:<erreur>",
    consigné dans le manifeste d'archive du relevé.
    """
    cfg = smtp_settings()
    if not cfg["from_addr"]:
        return "skipped:EMAIL_FROM absent"
    if not to_addrs:
        return "skipped:aucun destinataire"
    if not cfg["user"] or not cfg["pwd"]:
        return "skipped:identifiants SMTP absents"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"MYJ Capital <{cfg['from_addr']}>"
    msg["To"] = ", ".join(to_addrs)
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    try:
        if cfg["use_tls"]:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as s:
                s.ehlo(); s.starttls(context=ctx); s.login(cfg["user"], cfg["pwd"])
                s.sendmail(cfg["from_addr"], to_addrs, msg.as_bytes())
        else:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx) as s:
                s.login(cfg["user"], cfg["pwd"])
                s.sendmail(cfg["from_addr"], to_addrs, msg.as_bytes())
        return "sent"
    except Exception as exc:  # noqa: BLE001 — statut consigné, run non interrompu
        return f"failed:{exc}"
