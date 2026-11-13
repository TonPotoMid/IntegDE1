# Mini-projet DE : intégration continue d'une pipeline data

Pipeline : **CSV → S3 local (SeaweedFS) → traitement Python → PostgreSQL → dashboard Grafana**,
testée et exécutée par **GitHub Actions** (CI), puis construite et déployée avec Docker (CD).

```
generate ──► upload S3 ──► download (retry) ──► parse/validate ──► process (pur) ──► insert DB (retry, atomique)
                                   │                                                      │
                                   └──── skip si fichier déjà traité (nom ou checksum) ◄──┘
```

## Structure

| Fichier | Rôle |
|---|---|
| `pipeline/generate.py` | Génère 3 CSV de 5 à 7 transactions **déterministes** (pas d'aléatoire) |
| `pipeline/loader.py` | **Chargement** : parsing et validation du CSV, checksum |
| `pipeline/processing.py` | **Traitements purs** : sommes envoyées par IBAN et par banque, sommes reçues par IBAN, flag si montant > 5000 |
| `pipeline/db.py` | Schéma, idempotence, insertion transactionnelle avec retry |
| `pipeline/storage.py` | Client S3 (SeaweedFS) : bucket, upload, listing, téléchargement avec retry |
| `pipeline/retry.py` | Décorateur de retry avec backoff exponentiel |
| `pipeline/faults.py` | Injection de pannes (`SIMULATE_INSERT_FAILURES`, `SIMULATE_DOWNLOAD_FAILURES`) |
| `pipeline/main.py` | Orchestration (CLI) et mode planifié `--loop` |
| `sql/schema.sql` | Modèle relationnel |
| `tests/unit` | Tests unitaires (traitements, parsing, génération, retry) |
| `tests/integration` | Tests d'intégration sur un S3 et un PostgreSQL réels |
| `.github/workflows/ci.yml` | Pipeline CI |
| `.github/workflows/cd.yml` | Pipeline CD (image GHCR, smoke test prod, déploiement VM) |
| `grafana/` | Datasource et dashboard provisionnés |

> Le format de l'énoncé ne contient pas de montant ; une colonne `montant` (et un `transaction_id`)
> a été ajoutée, car elle est indispensable aux traitements demandés.

## Modèle de données

- `processed_files(file_key PK, checksum UNIQUE, row_count, processed_at)` : journal des fichiers traités
- `transactions(transaction_id PK, …, montant, is_flagged, source_file FK → processed_files)`
- `sent_by_iban(iban, total)`, `sent_by_bank(banque, total)`, `received_by_iban(iban, total)` : agrégats incrémentaux

## Ne jamais traiter deux fois le même fichier

1. Avant le traitement, on cherche le fichier dans `processed_files` **par nom ou par checksum SHA-256**. On ignore donc aussi un même contenu renommé.
2. L'insertion des transactions, la mise à jour des agrégats et l'ajout dans `processed_files` se font dans **une seule transaction SQL**.
   Si une erreur survient au milieu, un **rollback** a lieu et rien n'est marqué traité. Le retry repart donc d'un état propre, sans doublon.
3. `INSERT … ON CONFLICT DO NOTHING` sur `processed_files` protège en plus contre deux exécutions concurrentes.

## Retry

- **Insertion DB** (N1.7) : `insert_with_retry` utilise jusqu'à `RETRY_ATTEMPTS` tentatives avec backoff exponentiel et une nouvelle connexion à chaque tentative.
  Pour simuler un bug : `SIMULATE_INSERT_FAILURES=2` fait échouer les 2 premières insertions **après** une écriture partielle, ce qui démontre le rollback.
- **Téléchargement S3** (N2.4) : `storage.download` est retenté. Pour simuler : `SIMULATE_DOWNLOAD_FAILURES=N`.
- Si toutes les tentatives échouent, la pipeline s'arrête en erreur sans rien insérer. Le prochain run (ou le prochain cycle `--loop`) rattrape le fichier.

## Lancer en local

```bash
pip install -r requirements-dev.txt
docker compose up -d --wait db s3                     # S3 local + PostgreSQL
python -m pipeline.main all                           # generate + upload + init-db + process
pytest tests/unit                                     # tests unitaires
pytest tests/integration                              # tests d'intégration
docker compose --profile dashboard up -d grafana      # dashboard sur http://localhost:3000 (GRAFANA_PORT pour changer)
```

Setup « prod » (niveau 3) : `docker compose --profile prod up -d --build` démarre S3, DB, Grafana et le
service de traitement, qui relance `process` toutes les 60 s. Il suffit de déposer un CSV dans le bucket.

## CI (`ci.yml`)

1. Lint (ruff) et tests unitaires
2. Démarrage de SeaweedFS et PostgreSQL (docker compose)
3. Génération des CSV, upload S3, setup DB
4. Traitement **avec pannes simulées** (2 échecs d'insertion, 1 échec de téléchargement), rattrapées par les retries
5. Test d'intégration de l'état de la base (valeurs attendues calculées à la main dans `tests/expected.py`)
6. Relance du traitement : on vérifie qu'aucun fichier n'est retraité et que les valeurs ne sont pas doublées
7. Tests bout-en-bout : retry, retries épuisés puis rattrapage, contenu renommé, traitement incrémental

## CD (`cd.yml`, niveau 3)

Après une CI verte sur `main` : build et push de l'image vers GHCR, puis smoke test du profil `prod`
(le service planifié doit traiter seul les fichiers déposés). Ensuite, déploiement sur une VM par SSH
si les secrets `VM_HOST`, `VM_USER` et `VM_SSH_KEY` sont configurés.

## Scénarios d'échec (N1.6), à capturer en screenshot

Deux branches contiennent chacune un bug volontaire. Leur run CI échoue ; c'est ce run qu'il faut capturer :

| Branche | Bug | Étape qui échoue |
|---|---|---|
| `demo/bug-generation` | Le générateur écrit un montant faux pour T007 (`1500.00` au lieu de `15000.00`) | Tests unitaires et test d'état de la DB : les sommes ne correspondent plus |
| `demo/bug-processing` | Seuil de flag en `>=` au lieu de `>` (T004 = 5000.00 devient flaggé) | `test_flag_threshold_is_strict`, `test_flagged_ids` |
| `demo/bug-insertion` | Panne d'insertion persistante (`SIMULATE_INSERT_FAILURES=99`) | Étape 5 : les 4 tentatives échouent, puis rollback (N1.7) |

Captures : `docs/screenshots/`.
