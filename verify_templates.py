#!/usr/bin/env python3
"""
Vérifie que les modèles de relevé archivés n'ont pas été modifiés.

    python verify_templates.py            # contrôle (code retour 1 si anomalie)
    python verify_templates.py --update   # (re)génère templates/LOCK.json

Ce contrôle est exécuté :
  - en CI sur chaque push (workflow templates-lock.yml) ;
  - au démarrage de monthly_report.py, avant tout envoi.

Il matérialise la règle d'archivage : un modèle déjà utilisé pour un relevé
envoyé ne se modifie pas — on crée une version suivante.
"""

import sys

import templates


def main() -> int:
    if "--update" in sys.argv:
        empreintes = templates.write_lock()
        print("templates/LOCK.json mis à jour :")
        for version, digest in empreintes.items():
            marque = "  (courante)" if version == templates.LATEST else ""
            print(f"  {version}  {digest}{marque}")
        return 0

    problemes = templates.verify()
    if problemes:
        print("❌ Contrôle d'intégrité des modèles échoué :", file=sys.stderr)
        for p in problemes:
            print(f"   - {p}", file=sys.stderr)
        print(
            "\n   Un modèle déjà publié ne doit jamais être édité.\n"
            "   → Créez templates/releve_vN+1.py, enregistrez-le dans\n"
            "     templates/__init__.py, puis lancez :\n"
            "       python verify_templates.py --update",
            file=sys.stderr,
        )
        return 1

    print(f"✅ {len(templates.REGISTRY)} modèles conformes au verrou "
          f"(courant : {templates.LATEST}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
