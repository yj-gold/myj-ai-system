#!/usr/bin/env python3
"""
MYJ Capital — génération automatique des relevés mensuels clients.

Pour chaque client « en cours » du registre (`clients.json`) :
  1. connexion à son compte IG avec ses propres identifiants ;
  2. extraction des opérations du mois échu ;
  3. calcul des métriques de performance ;
  4. rendu du relevé avec le modèle ARCHIVÉ auquel le client est rattaché,
     enrichi de l'historique de ses relevés précédents ;
  5. archivage (HTML + manifeste + analytics + CSV) ;
  6. envoi e-mail, avec consignation du statut dans le manifeste.

Le run est idempotent : un relevé déjà archivé pour la période n'est pas
régénéré (sauf `--force`), ce qui rend le lancement mensuel automatique sûr.

Exemples
--------
  python monthly_report.py                       # mois échu, tous les clients actifs
  python monthly_report.py --month 2026-07       # une période précise
  python monthly_report.py --client dupont-jean  # un seul client
  python monthly_report.py --dry-run             # génère et archive, n'envoie rien
  python monthly_report.py --verify 2026-07      # rejoue l'archive et vérifie les empreintes
"""

import argparse
import calendar
import logging
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import archive_store
import clients as client_registry
import templates
from analytics import TradingAnalytics
from data_extractor import DataExtractor
from email_report import send_html
from ig_client import IGAPIError, IGClient
from templates.releve_v2 import periode_fr

logger = logging.getLogger("monthly_report")


# ── Périodes ─────────────────────────────────────────────────────────────────

def previous_month(today: Optional[date] = None) -> str:
    """Mois échu au format YYYY-MM (le run du 1er mars produit 2026-02)."""
    today = today or date.today()
    y, m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    return f"{y:04d}-{m:02d}"


def period_bounds(period: str) -> Tuple[str, str]:
    """'2026-07' → ('2026-07-01', '2026-07-31')."""
    y, m = (int(x) for x in period.split("-"))
    return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"


# ── Génération d'un relevé ───────────────────────────────────────────────────

def build_releve(client: Dict[str, Any], period: str,
                 archive_root: Optional[str] = None) -> Dict[str, Any]:
    """Extrait, calcule, rend et archive le relevé d'un client. Renvoie le manifeste."""
    from_date, to_date = period_bounds(period)
    creds = client_registry.credentials(client)
    version = templates.resolve_version(client.get("template", "latest"))
    renderer = templates.get_renderer(version)

    ig = IGClient(
        api_key=creds["api_key"],
        username=creds["username"],
        password=creds["password"],
        base_url=creds["base_url"],
        account_id=creds["account_id"],
    )
    try:
        ig.login()
        extractor = DataExtractor(ig)
        accounts = extractor.get_accounts()
        transactions = extractor.get_transactions(from_date=from_date, to_date=to_date)

        if transactions.empty:
            analytics = {"error": f"Aucune opération sur la période {periode_fr(period)}."}
        else:
            analytics = TradingAnalytics(transactions).calculate_all()
    finally:
        ig.logout()

    history = archive_store.history(client["id"], before=period, root=archive_root)

    html = renderer(
        analytics=analytics,
        accounts=accounts,
        from_date=from_date,
        to_date=to_date,
        client=client,
        history=history,
    )

    return archive_store.save(
        client=client,
        period=period,
        html=html,
        analytics=analytics,
        template_version=version,
        template_sha256=templates.template_sha256(version),
        from_date=from_date,
        to_date=to_date,
        recipients=client_registry.recipients(client),
        accounts=accounts,
        transactions=None if transactions.empty else transactions,
        root=archive_root,
    )


def subject_for(client: Dict[str, Any], period: str,
                manifest: Dict[str, Any]) -> str:
    net = manifest["metrics"]["net_pnl"]
    signe = "+" if net >= 0 else ""
    return (f"MYJ Capital — Relevé {periode_fr(period)} — "
            f"{client.get('name','')} — P&L {signe}{net:,.2f}")


# ── Vérification de reproductibilité ─────────────────────────────────────────

def verify_period(period: str, only: Optional[List[str]] = None,
                  registry_path: Optional[str] = None,
                  archive_root: Optional[str] = None) -> int:
    """Rejoue les relevés archivés depuis leurs analytics et compare les empreintes.

    C'est la preuve que l'archive du modèle fonctionne : le HTML régénéré
    aujourd'hui doit être identique (hors horodatage) à celui envoyé au client.
    """
    import json
    import os
    import re

    anomalies = 0
    for client in client_registry.load_clients(registry_path):
        if only and client["id"] not in only:
            continue
        manifest = archive_store.read_manifest(client["id"], period, archive_root)
        if not manifest:
            continue

        version = manifest["template_version"]
        empreinte_modele = templates.template_sha256(version)
        if empreinte_modele != manifest["template_sha256"]:
            print(f"  ❌ {client['id']} {period} : le modèle {version} a changé "
                  f"depuis l'envoi ({manifest['template_sha256'][:12]}… → "
                  f"{empreinte_modele[:12]}…)")
            anomalies += 1
            continue

        dossier = archive_store.period_dir(client["id"], period, archive_root)
        with open(os.path.join(dossier, "analytics.json"), encoding="utf-8") as fh:
            analytics = json.load(fh)
        with open(os.path.join(dossier, "releve.html"), encoding="utf-8") as fh:
            html_archive = fh.read()

        rejoue = templates.get_renderer(version)(
            analytics=analytics,
            accounts=archive_store.read_accounts(client["id"], period, archive_root),
            from_date=manifest["from_date"],
            to_date=manifest["to_date"],
            client=client,
            history=archive_store.history(client["id"], before=period, root=archive_root),
        )
        # L'horodatage d'édition est le seul élément volatil du rendu.
        norm = lambda h: re.sub(r"Édité le [^<]*", "Édité le —", h)  # noqa: E731
        if norm(rejoue) == norm(html_archive):
            print(f"  ✅ {client['id']} {period} : relevé reproductible "
                  f"(modèle {version})")
        else:
            print(f"  ⚠️  {client['id']} {period} : le rendu rejoué diffère "
                  f"de l'archive (modèle {version})")
            anomalies += 1
    return anomalies


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Relevés mensuels clients MYJ Capital",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--month", metavar="YYYY-MM", default=None,
                   help="Période à traiter (défaut : mois échu)")
    p.add_argument("--client", action="append", dest="only", metavar="ID",
                   help="Limiter à ce client (répétable)")
    p.add_argument("--clients-file", default=None,
                   help="Registre client (défaut : clients.json ou $CLIENTS_FILE)")
    p.add_argument("--archive-dir", default=None,
                   help="Racine de l'archive (défaut : ./archive ou $ARCHIVE_DIR)")
    p.add_argument("--force", action="store_true",
                   help="Régénérer même si le relevé est déjà archivé")
    p.add_argument("--dry-run", action="store_true",
                   help="Générer et archiver sans envoyer d'e-mail")
    p.add_argument("--no-email", action="store_true", help="Alias de --dry-run")
    p.add_argument("--verify", metavar="YYYY-MM", default=None,
                   help="Rejouer une période archivée et vérifier les empreintes")
    p.add_argument("--debug", action="store_true", help="Journalisation verbeuse")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )
    if not args.debug:
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Garde-fou : aucun envoi si un modèle déjà publié a été modifié.
    problemes = templates.verify()
    if problemes:
        print("❌ Modèles archivés altérés — run interrompu :", file=sys.stderr)
        for p in problemes:
            print(f"   - {p}", file=sys.stderr)
        print("   Lancez : python verify_templates.py", file=sys.stderr)
        return 1

    if args.verify:
        print(f"\n  Vérification des relevés archivés — {args.verify}\n")
        return 1 if verify_period(args.verify, args.only, args.clients_file,
                                  args.archive_dir) else 0

    period = args.month or previous_month()
    envoi = not (args.dry_run or args.no_email)

    try:
        actifs = client_registry.active_clients(args.clients_file, args.only)
    except client_registry.ClientConfigError as exc:
        print(f"\n  Registre client : {exc}\n", file=sys.stderr)
        return 1

    debut, fin = period_bounds(period)
    print(f"\n  Période      : {periode_fr(period)}  ({debut} → {fin})")
    print(f"  Clients      : {len(actifs)} actif(s)")
    print(f"  Modèle courant : {templates.LATEST}")
    print(f"  Archive      : {args.archive_dir or archive_store.ARCHIVE_DIR}")
    print(f"  Envoi e-mail : {'oui' if envoi else 'non (dry-run)'}\n")

    ok = ignores = erreurs = 0
    for client in actifs:
        cid = client["id"]
        if archive_store.exists(cid, period, args.archive_dir) and not args.force:
            print(f"  ↷ {cid:24s} déjà archivé pour {period} (--force pour régénérer)")
            ignores += 1
            continue

        try:
            print(f"  → {cid:24s} génération…")
            manifest = build_releve(client, period, args.archive_dir)
        except (IGAPIError, client_registry.ClientConfigError) as exc:
            print(f"  ✖ {cid:24s} échec : {exc}", file=sys.stderr)
            erreurs += 1
            continue
        except Exception as exc:  # noqa: BLE001 — un client en échec n'arrête pas le run
            logger.exception("Erreur inattendue pour %s", cid)
            print(f"  ✖ {cid:24s} échec inattendu : {exc}", file=sys.stderr)
            erreurs += 1
            continue

        net = manifest["metrics"]["net_pnl"]
        print(f"    modèle {manifest['template_version']} · "
              f"{manifest['metrics']['trades']} trades · P&L {net:+,.2f} · "
              f"archivé dans {archive_store.period_dir(cid, period, args.archive_dir)}")

        if envoi:
            destinataires = client_registry.recipients(client)
            html_path = archive_store.period_dir(cid, period, args.archive_dir) + "/releve.html"
            with open(html_path, encoding="utf-8") as fh:
                html = fh.read()
            statut = send_html(
                html=html,
                subject=subject_for(client, period, manifest),
                to_addrs=destinataires,
                reply_to=client.get("reply_to"),
            )
            archive_store.mark_sent(cid, period, statut, args.archive_dir)
            marque = "✓" if statut == "sent" else "!"
            print(f"    {marque} e-mail : {statut} → {', '.join(destinataires) or '—'}")
        ok += 1

    print(f"\n  Terminé — {ok} relevé(s) produit(s), {ignores} ignoré(s), "
          f"{erreurs} en échec.\n")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
