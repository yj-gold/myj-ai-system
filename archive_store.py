"""
Archive des relevés clients MYJ Capital.

Arborescence (racine surchargeable par ARCHIVE_DIR, défaut ./archive) ::

    archive/
      index.json                     registre global (client → périodes émises)
      <client_id>/
        2026-07/
          releve.html                le relevé exact envoyé au client
          manifest.json              qui / quoi / quel modèle / quelles empreintes
          analytics.json             toutes les métriques calculées
          accounts.json              état du compte IG au moment de l'édition
          transactions.csv           données brutes de la période

Le `manifest.json` est la pièce maîtresse : il enregistre la version du modèle
utilisée, l'empreinte SHA-256 du code de ce modèle, le commit du moteur et
l'empreinte du HTML produit. Un relevé archivé est donc reproductible : on sait
exactement quel code l'a généré, et `verify_templates.py` garantit que ce code
n'a pas changé depuis.

C'est aussi la « base des relevés précédents » : `history()` relit les
manifestes des mois antérieurs pour alimenter le comparatif du relevé courant.
"""

import csv
import hashlib
import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "./archive")
INDEX_NAME = "index.json"


# ── Chemins ──────────────────────────────────────────────────────────────────

def client_dir(client_id: str, root: Optional[str] = None) -> str:
    return os.path.join(root or ARCHIVE_DIR, client_id)


def period_dir(client_id: str, period: str, root: Optional[str] = None) -> str:
    return os.path.join(client_dir(client_id, root), period)


def exists(client_id: str, period: str, root: Optional[str] = None) -> bool:
    """Un relevé a-t-il déjà été archivé pour ce client sur cette période ?"""
    return os.path.exists(
        os.path.join(period_dir(client_id, period, root), "manifest.json")
    )


# ── Utilitaires ──────────────────────────────────────────────────────────────

def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def engine_commit() -> str:
    """Commit git du moteur au moment de la génération (traçabilité)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _metrics_resume(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """Extrait les quelques métriques réutilisées par l'historique."""
    pm = analytics.get("pnl_metrics", {}) or {}
    ts = analytics.get("trade_statistics", {}) or {}
    sm = analytics.get("summary", {}) or {}
    dd = analytics.get("drawdown", {}) or {}
    return {
        "net_pnl": float(pm.get("net_pnl", 0) or 0),
        "gross_pnl": float(pm.get("gross_pnl", 0) or 0),
        "trades": int(sm.get("total_trades", ts.get("total_trades", 0)) or 0),
        "win_rate": float(ts.get("win_rate", 0) or 0),
        "profit_factor": float(ts.get("profit_factor", 0) or 0),
        "max_drawdown": float(dd.get("max_drawdown", 0) or 0),
    }


# ── Écriture ─────────────────────────────────────────────────────────────────

def save(
    client: Dict[str, Any],
    period: str,
    html: str,
    analytics: Dict[str, Any],
    template_version: str,
    template_sha256: str,
    from_date: str,
    to_date: str,
    recipients: Optional[List[str]] = None,
    email_status: str = "not_sent",
    accounts: Optional[List[Dict[str, Any]]] = None,
    transactions=None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    """Écrit le relevé et son manifeste, puis met à jour l'index global."""
    dossier = period_dir(client["id"], period, root)
    os.makedirs(dossier, exist_ok=True)

    chemin_html = os.path.join(dossier, "releve.html")
    with open(chemin_html, "w", encoding="utf-8") as fh:
        fh.write(html)

    with open(os.path.join(dossier, "analytics.json"), "w", encoding="utf-8") as fh:
        json.dump(analytics, fh, indent=2, ensure_ascii=False, default=str)

    # Le bandeau « compte » fait partie du relevé : on l'archive pour pouvoir
    # régénérer le document à l'identique (cf. monthly_report.py --verify).
    with open(os.path.join(dossier, "accounts.json"), "w", encoding="utf-8") as fh:
        json.dump(accounts or [], fh, indent=2, ensure_ascii=False, default=str)

    if transactions is not None and getattr(transactions, "empty", True) is False:
        transactions.to_csv(
            os.path.join(dossier, "transactions.csv"),
            index=False, quoting=csv.QUOTE_MINIMAL,
        )

    precedents = history(client["id"], before=period, root=root)
    cumul = sum(h["net_pnl"] for h in precedents)
    resume = _metrics_resume(analytics)

    manifest = {
        "client_id": client["id"],
        "client_name": client.get("name", ""),
        "account_ref": client.get("account_ref", ""),
        "period": period,
        "from_date": from_date,
        "to_date": to_date,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "template_version": template_version,
        "template_sha256": template_sha256,
        "engine_commit": engine_commit(),
        "html_sha256": _sha256_text(html),
        "recipients": recipients or [],
        "email_status": email_status,
        "metrics": resume,
        "cumulative_pnl": cumul + resume["net_pnl"],
    }
    with open(os.path.join(dossier, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    _update_index(manifest, root)
    return manifest


def mark_sent(client_id: str, period: str, status: str,
              root: Optional[str] = None) -> None:
    """Met à jour le statut d'envoi dans le manifeste après le SMTP."""
    chemin = os.path.join(period_dir(client_id, period, root), "manifest.json")
    if not os.path.exists(chemin):
        return
    with open(chemin, encoding="utf-8") as fh:
        manifest = json.load(fh)
    manifest["email_status"] = status
    manifest["email_status_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    _update_index(manifest, root)


# ── Lecture ──────────────────────────────────────────────────────────────────

def read_accounts(client_id: str, period: str,
                  root: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """État du compte tel qu'affiché dans le relevé archivé."""
    chemin = os.path.join(period_dir(client_id, period, root), "accounts.json")
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as fh:
        return json.load(fh)


def read_manifest(client_id: str, period: str,
                  root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    chemin = os.path.join(period_dir(client_id, period, root), "manifest.json")
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as fh:
        return json.load(fh)


def periods(client_id: str, root: Optional[str] = None) -> List[str]:
    """Périodes archivées pour un client, par ordre chronologique."""
    dossier = client_dir(client_id, root)
    if not os.path.isdir(dossier):
        return []
    return sorted(
        d for d in os.listdir(dossier)
        if os.path.isfile(os.path.join(dossier, d, "manifest.json"))
    )


def history(client_id: str, before: Optional[str] = None,
            root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Historique des relevés précédents, du plus ancien au plus récent.

    C'est la « base » qui alimente le comparatif du relevé courant :
    P&L mensuel, nombre de trades, taux de réussite, cumul depuis l'origine.
    """
    lignes: List[Dict[str, Any]] = []
    cumul = 0.0
    for p in periods(client_id, root):
        if before and p >= before:
            break
        manifest = read_manifest(client_id, p, root)
        if not manifest:
            continue
        m = manifest.get("metrics", {})
        cumul += float(m.get("net_pnl", 0) or 0)
        lignes.append({
            "period": p,
            "net_pnl": float(m.get("net_pnl", 0) or 0),
            "trades": int(m.get("trades", 0) or 0),
            "win_rate": float(m.get("win_rate", 0) or 0),
            "cumulative_pnl": cumul,
            "template_version": manifest.get("template_version", ""),
        })
    return lignes


# ── Index global ─────────────────────────────────────────────────────────────

def index_path(root: Optional[str] = None) -> str:
    return os.path.join(root or ARCHIVE_DIR, INDEX_NAME)


def load_index(root: Optional[str] = None) -> Dict[str, Any]:
    chemin = index_path(root)
    if not os.path.exists(chemin):
        return {"clients": {}}
    with open(chemin, encoding="utf-8") as fh:
        return json.load(fh)


def _update_index(manifest: Dict[str, Any], root: Optional[str] = None) -> None:
    index = load_index(root)
    fiche = index.setdefault("clients", {}).setdefault(
        manifest["client_id"],
        {"name": manifest.get("client_name", ""), "releves": {}},
    )
    fiche["name"] = manifest.get("client_name", fiche.get("name", ""))
    fiche["releves"][manifest["period"]] = {
        "generated_at": manifest["generated_at"],
        "template_version": manifest["template_version"],
        "template_sha256": manifest["template_sha256"],
        "html_sha256": manifest["html_sha256"],
        "engine_commit": manifest["engine_commit"],
        "email_status": manifest["email_status"],
        "net_pnl": manifest["metrics"]["net_pnl"],
    }
    index["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    os.makedirs(root or ARCHIVE_DIR, exist_ok=True)
    with open(index_path(root), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
