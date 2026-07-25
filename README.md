# oura

[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/oura-helm)](https://artifacthub.io/packages/search?repo=oura-helm)
[![CI](https://github.com/kgrubb/oura-helm-chart/actions/workflows/ci.yml/badge.svg)](https://github.com/kgrubb/oura-helm-chart/actions/workflows/ci.yml)

Helm chart that syncs [Oura Ring](https://ouraring.com/) API v2 data into PostgreSQL. It deploys a CronJob for scheduled collection (daily metrics, sleep, heart rate, workouts, and related tables) and refreshes Symptom Radar scores on each run.

Optional features:

- Postgres bootstrap (database and roles)
- Grafana dashboard ConfigMap (sidecar labels)
- Grafana Postgres datasource Secret

PostgreSQL and Grafana are not installed by this chart. Point `postgres.host` at a database you already run.

Chart packages are signed. Verify with the [public key](https://kgrubb.github.io/oura-helm-chart/public.key).

## Prerequisites

- Kubernetes 1.25+
- Helm 4
- A reachable PostgreSQL server
- An [Oura personal access token](https://cloud.ouraring.com/personal-access-tokens) or OAuth client credentials

## Installing the Chart

```bash
helm repo add kgrubb-oura https://kgrubb.github.io/oura-helm-chart
helm repo update
```

### Quickstart

Creates Secrets from values, bootstraps the database, and enables the Grafana dashboard and datasource:

```bash
helm install oura kgrubb-oura/oura -n monitoring --create-namespace \
  --set quickstart.enabled=true \
  --set postgres.host=postgres.postgres.svc.cluster.local \
  --set postgres.bootstrap.admin.password='ADMIN_PASSWORD' \
  --set postgres.password='APP_PASSWORD' \
  --set postgres.passwordRo='RO_PASSWORD' \
  --set auth.pat='OURA_PAT'
```

Replace the passwords and PAT. Set `postgres.host` to your Postgres service DNS name.

### Existing Secrets

```bash
kubectl -n monitoring create secret generic oura-db \
  --from-literal=password='APP_PASSWORD' \
  --from-literal=password-ro='RO_PASSWORD'

kubectl -n monitoring create secret generic oura-api \
  --from-literal=OURA_PAT='OURA_PAT'

helm install oura kgrubb-oura/oura -n monitoring --create-namespace \
  --set postgres.host=postgres.postgres.svc.cluster.local \
  --set postgres.existingSecret=oura-db \
  --set auth.existingSecret=oura-api
```

Enable optional features explicitly when needed:

```bash
helm upgrade --install oura kgrubb-oura/oura -n monitoring \
  --set postgres.existingSecret=oura-db \
  --set auth.existingSecret=oura-api \
  --set postgres.bootstrap.enabled=true \
  --set postgres.bootstrap.admin.existingSecret=postgres-admin \
  --set postgres.bootstrap.readOnlyUser=oura_ro \
  --set dashboard.enabled=true \
  --set dashboard.createDatasource=true \
  --set dashboard.datasource.password='RO_PASSWORD'
```

The admin Secret must include the key named by `postgres.bootstrap.admin.passwordKey` (default `password`). When `readOnlyUser` is set, the DB Secret must include `postgres.bootstrap.readOnlyPasswordKey` (default `password-ro`). With `dashboard.createDatasource` and an existing DB Secret, set `dashboard.datasource.password` so the chart can embed credentials in the Grafana provisioning Secret.

Bootstrap creates roles on first install using the passwords you supply. Later upgrades do not rotate existing role passwords. To change a password, update the Secret or values and run `ALTER ROLE ... PASSWORD` (or recreate the role).

### Values file

```bash
helm install oura kgrubb-oura/oura -n monitoring --create-namespace -f my-values.yaml
```

## Uninstalling the Chart

```bash
helm uninstall oura -n monitoring
```

Hook Jobs are removed with the release. In OAuth mode, a token PVC kept with `helm.sh/resource-policy: keep` must be deleted separately if you no longer need it.

## Upgrading from 0.x

Remove any reused `image.repository=ghcr.io/astral-sh/uv` or `image.tag=python3.12-alpine` values before upgrading. Chart validation fails until those overrides are cleared.

## Configuration

Full defaults live in [charts/oura/values.yaml](charts/oura/values.yaml). Common settings:

| Parameter | Description | Default |
| --- | --- | --- |
| `quickstart.enabled` | Create Secrets from values and enable bootstrap, dashboard, and datasource | `false` |
| `schedule` | Cron expression for the collector | `*/15 * * * *` |
| `timeZone` | CronJob time zone | `UTC` |
| `image.repository` | Collector image | `ghcr.io/kgrubb/oura-collector` |
| `image.tag` | Image tag (empty uses `appVersion`) | `""` |
| `postgres.host` | PostgreSQL hostname | `postgres` |
| `postgres.database` | Database name | `oura` |
| `postgres.user` | Application (read/write) role | `oura` |
| `postgres.existingSecret` | Existing DB password Secret | `""` |
| `postgres.password` / `passwordRo` | Inline passwords when not using `existingSecret` | `""` |
| `postgres.bootstrap.enabled` | Create database and roles on install/upgrade | `false` |
| `postgres.bootstrap.readOnlyUser` | Optional RO role (`oura_ro`). Quickstart defaults to `oura_ro` when the chart creates the DB Secret | `""` |
| `auth.mode` | `pat` or `oauth` | `pat` |
| `auth.existingSecret` | Existing Oura credentials Secret | `""` |
| `auth.pat` | Inline PAT when not using `existingSecret` | `""` |
| `dashboard.enabled` | Publish Grafana dashboard ConfigMap | `false` |
| `dashboard.createDatasource` | Publish Grafana datasource Secret | `false` |
| `dashboard.datasourceUid` | Grafana datasource UID referenced by the dashboard | `oura-postgres` |
| `backfill.enabled` | One-shot Job for historical sync | `false` |
| `backfill.startDate` | Earliest day to fetch when backfilling | `2015-01-01` |

### Authentication

PAT (default): store the token under key `OURA_PAT`, or set `auth.pat` / `auth.patKey`.

OAuth: set `auth.mode=oauth` and provide a Secret with client id and secret keys. The chart mounts a PVC for the refresh token JSON. Authorize the Oura app with:

```text
email personal daily heartrate spo2 workout stress heart_health
```

### Historical backfill

```bash
helm upgrade oura kgrubb-oura/oura -n monitoring \
  --reuse-values \
  --set backfill.enabled=true \
  --set backfill.startDate='2015-01-01'
```

Set `backfill.enabled=false` again after the Job finishes if you do not want it recreated on later upgrades.

## Development

```bash
uv sync --group dev
uv run ruff check src tests && uv run ruff format src tests && uv run pytest
./scripts/versions.sh check
helm lint charts/oura --strict -f ci/values.yaml && helm unittest charts/oura
```
