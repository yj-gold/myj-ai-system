# Relevés mensuels clients — mode d'emploi

Génération automatique, chaque mois, du relevé de performance de chaque client
en cours, à partir du modèle utilisé pour les relevés précédents, avec archivage
complet et vérifiable.

---

## 1. Vue d'ensemble

```
clients.json ──┐
               ├─► monthly_report.py ──► IG API ──► analytics ──┐
archive/ ──────┘         (mois échu)                            │
   (relevés antérieurs → historique & cumul)                    ▼
                                            templates/releve_vN.py (modèle gelé)
                                                                │
                                    ┌───────────────────────────┴──────────┐
                                    ▼                                      ▼
                       archive/<client>/<AAAA-MM>/                    e-mail client
                         releve.html · manifest.json
                         analytics.json · accounts.json
                         transactions.csv
```

Trois garanties :

1. **Continuité** — chaque relevé repart de la base des relevés précédents
   (P&L mensuel, cumul depuis l'origine, comparatif m/m-1).
2. **Idempotence** — un relevé déjà archivé pour la période n'est ni régénéré
   ni renvoyé (sauf `--force`). Le lancement automatique est donc sans risque
   de doublon.
3. **Reproductibilité** — le modèle qui a produit chaque relevé est conservé,
   verrouillé par empreinte, et le relevé peut être régénéré à l'identique
   des années plus tard.

---

## 2. Comment l'archive du modèle est conservée

C'est le point central : **le modèle est du code versionné, gelé et verrouillé.**

| Élément | Où | Rôle |
|---|---|---|
| Modèles | `templates/releve_v1.py`, `releve_v2.py`, … | Une version = un fichier autonome. Une version publiée n'est **jamais** modifiée. |
| Registre | `templates/__init__.py` | `REGISTRY` (toutes les versions, on n'en retire aucune) et `LATEST` (version courante). |
| Verrou | `templates/LOCK.json` | Empreinte SHA-256 du code de chaque modèle. |
| Contrôle | `verify_templates.py` | Compare code et verrou. Échoue si un modèle publié a bougé. Exécuté en CI (`.github/workflows/verrou-modeles.yml`) **et** au démarrage de chaque run mensuel, avant tout envoi. |
| Journal | `templates/CHANGELOG.md` | Ce que contient chaque version, date de gel, procédure de création d'une v(N+1). |
| Traçabilité | `archive/<client>/<AAAA-MM>/manifest.json` | Pour chaque relevé envoyé : version du modèle, empreinte du modèle, commit du moteur, empreinte du HTML, destinataires, statut d'envoi. |

Autrement dit : **on ne modifie pas un modèle, on en publie un nouveau.**
Si vous éditez `releve_v2.py` après un premier envoi, le run mensuel refuse de
démarrer et la CI passe au rouge, avec le message expliquant qu'il faut créer
une `v3`. Un client peut rester épinglé sur une version (`"template": "v2"`)
pendant que les autres suivent `"latest"`.

Vérifier a posteriori qu'un relevé envoyé est bien reproductible :

```bash
python monthly_report.py --verify 2026-07
#   ✅ dupont-jean 2026-07 : relevé reproductible (modèle v2)
```

Le HTML est régénéré depuis `analytics.json` + `accounts.json` archivés avec le
modèle de l'époque, puis comparé au HTML réellement envoyé (seul l'horodatage
d'édition est neutralisé).

---

## 3. Mise en route

### a. Déclarer les clients en cours

```bash
cp clients.example.json clients.json
```

```json
{
  "clients": [
    {
      "id": "dupont-jean",
      "name": "Jean Dupont",
      "status": "active",
      "account_ref": "IG-ABC12",
      "mandate": "Mandat discrétionnaire — CTA Trend Following",
      "since": "2026-01",
      "template": "latest",
      "email_to": ["jean.dupont@example.com"],
      "email_cc": ["backoffice@myjcapital.com"],
      "ig": {
        "account_type": "LIVE",
        "account_id": "ABC12",
        "api_key_env": "IG_API_KEY_DUPONT",
        "username_env": "IG_USERNAME_DUPONT",
        "password_env": "IG_PASSWORD_DUPONT"
      }
    }
  ]
}
```

- `status: "active"` = client en cours, inclus dans le run mensuel ;
  `"inactive"` = sorti du périmètre, mais ses relevés restent archivés.
- **Aucun secret dans ce fichier** : les identifiants IG sont désignés par le
  *nom* de la variable d'environnement qui les porte. Si plusieurs comptes
  clients dépendent d'un même login IG, omettez les champs `*_env` et
  renseignez seulement `account_id` : les identifiants globaux du `.env`
  seront utilisés.
- `clients.json` est ignoré par git par défaut (noms et e-mails clients). Si
  vous voulez en garder l'historique, retirez la ligne du `.gitignore` — dépôt
  privé uniquement.

### b. Compléter le `.env`

Reprendre `.env.example` : identifiants IG, SMTP, plus `CLIENTS_FILE` et
`ARCHIVE_DIR`.

### c. Premier lancement à blanc

```bash
pip install -r requirements.txt
python verify_templates.py                 # modèles conformes
python test_releves.py                     # chaîne de bout en bout, hors ligne
python preview_releve.py                   # aperçu visuel → preview_releve.html
python monthly_report.py --month 2026-07 --dry-run   # génère et archive, n'envoie rien
```

Ouvrez `archive/<client>/2026-07/releve.html`, puis relancez sans `--dry-run`
quand le rendu vous convient.

---

## 4. Le run mensuel

```bash
python monthly_report.py                     # mois échu, tous les clients actifs
python monthly_report.py --month 2026-07     # période précise
python monthly_report.py --client dupont-jean
python monthly_report.py --force             # régénère un relevé déjà archivé
python monthly_report.py --dry-run           # sans envoi
python monthly_report.py --verify 2026-07    # contrôle de reproductibilité
```

Le run traite le **mois échu** (lancé le 3 mars → relevé de février), client par
client : un échec sur un client n'interrompt pas les autres, et le statut
d'envoi est consigné dans chaque manifeste.

### Automatisation

**GitHub Actions** — `.github/workflows/releves-mensuels.yml`, le 3 de chaque
mois à 06:00 UTC, déclenchable aussi à la main (`workflow_dispatch`).
Secrets à créer dans le dépôt :

| Secret | Contenu |
|---|---|
| `CLIENTS_JSON` | contenu intégral de `clients.json` |
| `IG_API_KEY`, `IG_USERNAME`, `IG_PASSWORD` | identifiants IG globaux |
| `IG_*_DUPONT`, … | identifiants IG propres à un client (un jeu par client) |
| `EMAIL_FROM`, `EMAIL_SMTP_*` | envoi SMTP |

L'archive est restaurée puis re-déposée en artefact GitHub (90 jours). Pour une
conservation longue durée, remplacez ces deux étapes par une synchronisation
vers votre stockage (S3, Drive, NAS) — les deux étapes sont commentées dans le
workflow.

**Serveur / poste local** — via cron :

```cron
0 6 3 * * cd /chemin/myj-ai-system && .venv/bin/python monthly_report.py >> logs/releves.log 2>&1
```

---

## 5. Où vivent les données

| Contenu | Emplacement | Suivi par git |
|---|---|---|
| Modèles de relevé + verrou + journal | `templates/` | **oui** (c'est l'archive du modèle) |
| Moteur (extraction, analytics, envoi) | racine du dépôt | oui |
| Registre client | `clients.json` | non (par défaut) |
| Relevés émis, manifestes, données | `archive/` | non |
| Identifiants | `.env` / secrets GitHub | non |

`archive/` contient des données financières nominatives : gardez-le sur un
support sauvegardé et à accès restreint (`ARCHIVE_DIR` pointe où vous voulez),
et conservez-le au moins aussi longtemps que vos obligations de conservation
des relevés clients l'exigent.

---

## 6. Faire évoluer la présentation

Voir `templates/CHANGELOG.md`. En résumé : copier la version courante en
`releve_v{N+1}.py`, modifier, déclarer dans `templates/__init__.py`, contrôler
avec `preview_releve.py`, puis `python verify_templates.py --update`.
Les relevés déjà envoyés restent liés à leur version d'origine.
