"""
Registre des clients MYJ Capital pour les relevés mensuels.

Le registre est un fichier JSON (par défaut `clients.json`, surchargeable via
la variable d'environnement `CLIENTS_FILE`). Il ne contient **aucun secret** :
les identifiants IG sont référencés par le NOM de la variable d'environnement
qui les porte, jamais par leur valeur.

Voir `clients.example.json` pour le format complet.
"""

import json
import os
from typing import Any, Dict, List, Optional

import config
import templates

DEFAULT_FILE = os.getenv("CLIENTS_FILE", "clients.json")

_REQUIRED = ("id", "name")


class ClientConfigError(Exception):
    """Registre client invalide ou identifiants manquants."""


def load_clients(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Charge et valide le registre complet (actifs et inactifs)."""
    path = path or DEFAULT_FILE
    if not os.path.exists(path):
        raise ClientConfigError(
            f"Registre client introuvable : {path}\n"
            f"  → Copiez clients.example.json vers {path} et complétez-le."
        )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    clients = data.get("clients", data if isinstance(data, list) else [])
    if not clients:
        raise ClientConfigError(f"Aucun client déclaré dans {path}.")

    vus = set()
    for c in clients:
        for champ in _REQUIRED:
            if not c.get(champ):
                raise ClientConfigError(
                    f"Champ obligatoire manquant « {champ} » dans {path} : {c}"
                )
        if c["id"] in vus:
            raise ClientConfigError(f"Identifiant client dupliqué : {c['id']}")
        vus.add(c["id"])

        version = c.get("template", "latest")
        if version not in ("latest", "") and version not in templates.REGISTRY:
            raise ClientConfigError(
                f"Client {c['id']} : modèle « {version} » inconnu "
                f"(disponibles : {', '.join(sorted(templates.REGISTRY))})"
            )
        c.setdefault("status", "active")
        c.setdefault("template", "latest")
        c.setdefault("email_to", [])
        c.setdefault("ig", {})
    return clients


def active_clients(path: Optional[str] = None,
                   only: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Clients « en cours » (status == active), filtrés éventuellement par id."""
    clients = [c for c in load_clients(path) if c.get("status") == "active"]
    if only:
        demandes = set(only)
        clients = [c for c in clients if c["id"] in demandes]
        inconnus = demandes - {c["id"] for c in clients}
        if inconnus:
            raise ClientConfigError(
                f"Client(s) inconnu(s) ou inactif(s) : {', '.join(sorted(inconnus))}"
            )
    return clients


def credentials(client: Dict[str, Any]) -> Dict[str, str]:
    """Résout les identifiants IG d'un client depuis l'environnement.

    Chaque champ accepte deux formes :
      - `<champ>_env` : nom de la variable d'environnement à lire (recommandé) ;
      - absent       : on retombe sur les identifiants globaux du .env
                       (cas de plusieurs comptes sous un même login IG).
    """
    ig = client.get("ig", {}) or {}

    def _resolve(cle: str, defaut: str) -> str:
        nom_var = ig.get(f"{cle}_env")
        if nom_var:
            valeur = os.getenv(nom_var, "")
            if not valeur:
                raise ClientConfigError(
                    f"Client {client['id']} : variable d'environnement "
                    f"« {nom_var} » vide ou absente."
                )
            return valeur
        return defaut

    api_key = _resolve("api_key", config.IG_API_KEY)
    username = _resolve("username", config.IG_USERNAME)
    password = _resolve("password", config.IG_PASSWORD)

    if not (api_key and username and password):
        raise ClientConfigError(
            f"Client {client['id']} : identifiants IG incomplets. "
            f"Renseignez ig.api_key_env / ig.username_env / ig.password_env "
            f"ou les valeurs globales IG_* du .env."
        )

    type_compte = (ig.get("account_type") or config.IG_ACCOUNT_TYPE).upper()
    base_url = config.BASE_URL_LIVE if type_compte == "LIVE" else config.BASE_URL_DEMO

    return {
        "api_key": api_key,
        "username": username,
        "password": password,
        "base_url": base_url,
        "account_id": ig.get("account_id") or config.IG_ACCOUNT_ID,
        "account_type": type_compte,
    }


def recipients(client: Dict[str, Any]) -> List[str]:
    """Destinataires du relevé (email_to + email_cc)."""
    to = client.get("email_to") or []
    if isinstance(to, str):
        to = [a.strip() for a in to.split(",") if a.strip()]
    cc = client.get("email_cc") or []
    if isinstance(cc, str):
        cc = [a.strip() for a in cc.split(",") if a.strip()]
    return list(dict.fromkeys([*to, *cc]))
