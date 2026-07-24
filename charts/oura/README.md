# oura

Helm chart that syncs [Oura Ring](https://ouraring.com/) API v2 data into PostgreSQL.

Full install guide: [repository README](https://github.com/kgrubb/oura-helm-chart#readme).

## TL;DR

```bash
helm repo add kgrubb-oura https://kgrubb.github.io/oura-helm-chart
helm repo update

helm install oura kgrubb-oura/oura -n monitoring --create-namespace \
  --set quickstart.enabled=true \
  --set postgres.host=postgres.postgres.svc.cluster.local \
  --set postgres.bootstrap.admin.password='ADMIN_PASSWORD' \
  --set postgres.password='APP_PASSWORD' \
  --set postgres.passwordRo='RO_PASSWORD' \
  --set auth.pat='OURA_PAT'
```

## Prerequisites

- Kubernetes 1.25+
- Helm 4
- PostgreSQL
- Oura PAT or OAuth credentials

## Configuration

| Parameter | Description | Default |
| --- | --- | --- |
| `quickstart.enabled` | Create Secrets from values and enable bootstrap, dashboard, datasource | `false` |
| `schedule` | Collector cron expression | `*/15 * * * *` |
| `postgres.host` | PostgreSQL hostname | `postgres` |
| `postgres.existingSecret` | DB password Secret (or set `postgres.password`) | `""` |
| `auth.mode` | `pat` or `oauth` | `pat` |
| `auth.existingSecret` | Oura credentials Secret (or set `auth.pat`) | `""` |
| `postgres.bootstrap.enabled` | Create database and roles | `false` |
| `postgres.bootstrap.readOnlyUser` | Optional RO role. Quickstart defaults to `oura_ro` when creating the DB Secret | `""` |
| `dashboard.enabled` | Grafana dashboard ConfigMap | `false` |
| `dashboard.createDatasource` | Grafana datasource Secret | `false` |
| `backfill.enabled` | One-shot historical sync Job | `false` |

Defaults: [values.yaml](values.yaml).
