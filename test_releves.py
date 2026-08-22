#!/usr/bin/env python3
"""
Tests hors-ligne de la chaîne de relevés (aucun appel réseau).

    python test_releves.py

Couvre :
  - intégrité des modèles archivés (LOCK.json) ;
  - archivage d'un relevé et contenu du manifeste ;
  - reconstitution de l'historique et du cumul depuis l'archive ;
  - idempotence du run mensuel ;
  - reproductibilité : un relevé archivé se régénère à l'identique.
"""

import json
import os
import shutil
import sys
import tempfile

import archive_store
import clients as client_registry
import monthly_report
import templates
from preview import MOCK, MOCK_ACCOUNTS

ECHECS = []


def check(condition: bool, libelle: str) -> None:
    print(("  ✅ " if condition else "  ❌ ") + libelle)
    if not condition:
        ECHECS.append(libelle)


def _analytics(net_pnl: float, trades: int, win_rate: float) -> dict:
    a = json.loads(json.dumps(MOCK))
    a["pnl_metrics"]["net_pnl"] = net_pnl
    a["summary"]["total_trades"] = trades
    a["trade_statistics"]["total_trades"] = trades
    a["trade_statistics"]["win_rate"] = win_rate
    return a


def main() -> int:
    racine = tempfile.mkdtemp(prefix="myj-archive-")
    registre = os.path.join(racine, "clients.json")
    client = {
        "id": "client-test", "name": "Client Test", "status": "active",
        "account_ref": "IG-TEST1", "mandate": "Mandat test",
        "template": "latest", "email_to": ["test@example.com"],
        "ig": {"account_id": "TEST1"},
    }
    with open(registre, "w", encoding="utf-8") as fh:
        json.dump({"clients": [client]}, fh)

    try:
        print("\n1. Intégrité des modèles archivés")
        check(templates.verify() == [], "LOCK.json conforme aux sources")
        check(templates.resolve_version("latest") == templates.LATEST,
              f"'latest' résout vers {templates.LATEST}")

        print("\n2. Archivage de trois relevés mensuels")
        jeux = [("2026-05", 1_240.00, 21, 52.4),
                ("2026-06", -430.50, 18, 44.4),
                ("2026-07", 2_115.75, 24, 58.3)]
        for periode, net, trades, wr in jeux:
            version = templates.resolve_version(client["template"])
            hist = archive_store.history(client["id"], before=periode, root=racine)
            analytics = _analytics(net, trades, wr)
            debut, fin = monthly_report.period_bounds(periode)
            html = templates.get_renderer(version)(
                analytics=analytics, accounts=MOCK_ACCOUNTS,
                from_date=debut, to_date=fin, client=client, history=hist,
            )
            manifest = archive_store.save(
                client=client, period=periode, html=html, analytics=analytics,
                template_version=version,
                template_sha256=templates.template_sha256(version),
                from_date=debut, to_date=fin,
                recipients=client_registry.recipients(client),
                accounts=MOCK_ACCOUNTS, root=racine,
            )
            check(manifest["metrics"]["net_pnl"] == net,
                  f"{periode} archivé (P&L {net:+,.2f}, modèle {version})")

        check(os.path.exists(os.path.join(racine, "client-test", "2026-07",
                                          "releve.html")),
              "le HTML envoyé est conservé dans l'archive")
        m = archive_store.read_manifest("client-test", "2026-07", racine)
        check(bool(m["template_sha256"]) and bool(m["html_sha256"]),
              "le manifeste porte les empreintes du modèle et du rendu")
        check(m["engine_commit"] != "", "le manifeste porte le commit du moteur")

        print("\n3. Historique reconstitué depuis l'archive")
        hist = archive_store.history("client-test", before="2026-07", root=racine)
        check([h["period"] for h in hist] == ["2026-05", "2026-06"],
              "les deux mois antérieurs sont retrouvés, dans l'ordre")
        check(abs(hist[-1]["cumulative_pnl"] - 809.50) < 0.01,
              f"cumul depuis l'origine correct ({hist[-1]['cumulative_pnl']:+,.2f})")
        cumul_total = archive_store.read_manifest("client-test", "2026-07",
                                                  racine)["cumulative_pnl"]
        check(abs(cumul_total - 2_925.25) < 0.01,
              f"cumul du relevé courant correct ({cumul_total:+,.2f})")

        print("\n4. Idempotence du run mensuel")
        check(archive_store.exists("client-test", "2026-07", racine),
              "un relevé déjà produit est détecté (pas de doublon d'envoi)")
        check(not archive_store.exists("client-test", "2026-08", racine),
              "une période non traitée n'est pas marquée comme faite")

        print("\n5. Reproductibilité du relevé archivé")
        anomalies = monthly_report.verify_period("2026-07", registry_path=registre,
                                                 archive_root=racine)
        check(anomalies == 0, "le relevé se régénère à l'identique depuis l'archive")

        print("\n6. Index global")
        index = archive_store.load_index(racine)
        fiche = index["clients"]["client-test"]["releves"]
        check(sorted(fiche) == ["2026-05", "2026-06", "2026-07"],
              "l'index recense les trois relevés")
        check(all(v["template_version"] for v in fiche.values()),
              "l'index consigne la version de modèle de chaque relevé")

    finally:
        shutil.rmtree(racine, ignore_errors=True)

    print()
    if ECHECS:
        print(f"❌ {len(ECHECS)} test(s) en échec :")
        for e in ECHECS:
            print(f"   - {e}")
        return 1
    print("✅ Tous les tests passent.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
