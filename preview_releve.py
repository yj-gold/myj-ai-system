#!/usr/bin/env python3
"""
Aperçu du relevé mensuel client (modèle courant), sans toucher à IG.

    python preview_releve.py            # modèle courant (templates.LATEST)
    python preview_releve.py v1         # une version archivée précise

Génère `preview_releve.html` avec des données de démonstration et un
historique factice de trois mois — utile pour valider un nouveau modèle
avant de le geler.
"""

import sys

import templates
from preview import MOCK, MOCK_ACCOUNTS

CLIENT_DEMO = {
    "id": "demo-client",
    "name": "Jean Dupont",
    "account_ref": "IG-ABC12",
    "mandate": "Mandat discrétionnaire — CTA Trend Following",
}

HISTORIQUE_DEMO = [
    {"period": "2026-04", "net_pnl": 1_240.00, "trades": 21, "win_rate": 52.4,
     "cumulative_pnl": 1_240.00},
    {"period": "2026-05", "net_pnl": -430.50, "trades": 18, "win_rate": 44.4,
     "cumulative_pnl": 809.50},
    {"period": "2026-06", "net_pnl": 2_115.75, "trades": 24, "win_rate": 58.3,
     "cumulative_pnl": 2_925.25},
]


def main() -> int:
    version = sys.argv[1] if len(sys.argv) > 1 else templates.LATEST
    html = templates.get_renderer(version)(
        analytics=MOCK,
        accounts=MOCK_ACCOUNTS,
        from_date="2026-07-01",
        to_date="2026-07-31",
        client=CLIENT_DEMO,
        history=HISTORIQUE_DEMO,
    )
    sortie = "preview_releve.html"
    with open(sortie, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"Aperçu du modèle {templates.resolve_version(version)} → {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
