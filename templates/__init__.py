"""
Registre des modèles de relevé MYJ Capital.

Principe d'archivage
--------------------
Chaque modèle est un module `releve_vN.py` **gelé** : une fois qu'un relevé a
été envoyé à un client avec cette version, le fichier ne doit plus jamais
changer. Son empreinte SHA-256 est enregistrée dans `LOCK.json` et vérifiée
par `verify_templates.py` (exécuté en CI et avant chaque envoi mensuel).

Conséquence pratique : n'importe quel relevé archivé peut être régénéré à
l'identique des années plus tard, puisque le code qui l'a produit est
conservé, versionné et verrouillé.

Pour faire évoluer le design : copier la dernière version en `releve_v{N+1}.py`,
la modifier, l'enregistrer ci-dessous, puis `python verify_templates.py --update`.
"""

import hashlib
import json
import os
from typing import Any, Callable, Dict, List

from . import releve_v1, releve_v2

_HERE = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(_HERE, "LOCK.json")

# Version → module de rendu. Ne jamais retirer une entrée : des relevés
# archivés y font référence.
REGISTRY: Dict[str, Any] = {
    "v1": releve_v1,
    "v2": releve_v2,
}

# Version utilisée pour les nouveaux clients (et pour ceux réglés sur "latest").
LATEST = "v2"


def get_renderer(version: str) -> Callable[..., str]:
    """Retourne la fonction `render` du modèle demandé."""
    key = LATEST if version in ("", "latest", None) else version
    if key not in REGISTRY:
        raise KeyError(
            f"Modèle inconnu : {version!r}. "
            f"Versions disponibles : {', '.join(sorted(REGISTRY))}"
        )
    return REGISTRY[key].render


def resolve_version(version: str) -> str:
    """Résout 'latest' en numéro de version réel (celui qui sera archivé)."""
    return LATEST if version in ("", "latest", None) else version


def template_source_path(version: str) -> str:
    return os.path.join(_HERE, f"releve_{resolve_version(version)}.py")


def template_sha256(version: str) -> str:
    """Empreinte du code source du modèle — inscrite dans chaque manifeste."""
    with open(template_source_path(version), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_lock() -> Dict[str, str]:
    if not os.path.exists(LOCK_FILE):
        return {}
    with open(LOCK_FILE, encoding="utf-8") as fh:
        return json.load(fh).get("templates", {})


def verify(strict: bool = True) -> List[str]:
    """Compare les empreintes actuelles au verrou. Retourne les anomalies."""
    lock = load_lock()
    problemes: List[str] = []
    for version in sorted(REGISTRY):
        actuel = template_sha256(version)
        attendu = lock.get(version)
        if attendu is None:
            if strict:
                problemes.append(f"{version} : absent de LOCK.json (jamais verrouillé)")
        elif attendu != actuel:
            problemes.append(
                f"{version} : MODÈLE ARCHIVÉ MODIFIÉ — "
                f"attendu {attendu[:12]}…, obtenu {actuel[:12]}…"
            )
    return problemes


def write_lock() -> Dict[str, str]:
    """(Re)génère LOCK.json à partir des sources actuelles."""
    data = {
        "_comment": "Empreintes SHA-256 des modèles gelés. "
                    "Une modification d'un modèle déjà publié doit être refusée : "
                    "créer une nouvelle version à la place.",
        "templates": {v: template_sha256(v) for v in sorted(REGISTRY)},
        "latest": LATEST,
    }
    with open(LOCK_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return data["templates"]
