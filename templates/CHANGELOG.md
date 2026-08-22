# Journal des modèles de relevé

Chaque version est un fichier `releve_vN.py` **gelé** dès son premier envoi
client. Une version publiée ne se modifie jamais : on en crée une nouvelle.
Les empreintes SHA-256 sont dans `LOCK.json`, contrôlées par
`verify_templates.py` (CI + avant chaque run mensuel).

| Version | Gelée le   | État    | Contenu |
|---------|-----------|---------|---------|
| `v1`    | 2026-08-22 | archivée | Modèle d'origine : rapport analytics MYJ Capital en anglais (KPI, P&L, risque, instruments, long/short, mensuel, jour de semaine, 20 dernières opérations). Rendu identique à celui des relevés déjà envoyés. |
| `v2`    | 2026-08-22 | **courante** | Relevé mensuel client : en-tête nominatif (nom, référence de compte, mandat, période en français), synthèse du mois avec comparatif m/m-1 et cumul depuis l'origine, section « Historique des relevés » alimentée par l'archive, libellés français, mention non contractuelle en pied de page. |

## Créer une v3

```bash
cp templates/releve_v2.py templates/releve_v3.py   # partir de la version courante
# éditer releve_v3.py (docstring : « VERSION 3 »)
# déclarer la version dans templates/__init__.py :
#   from . import releve_v3   →   REGISTRY["v3"] = releve_v3   →   LATEST = "v3"
python preview_releve.py v3          # contrôle visuel
python verify_templates.py --update  # verrouille la nouvelle empreinte
python test_releves.py               # non-régression
```

Les clients réglés sur `"template": "latest"` basculent sur la v3 au run
suivant. Ceux réglés sur `"v2"` (ou `"v1"`) gardent leur présentation, et
leurs anciens relevés restent régénérables à l'identique.
