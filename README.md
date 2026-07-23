# oura

[![Artifact Hub](https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/oura-helm)](https://artifacthub.io/packages/search?repo=oura-helm)
[![CI](https://github.com/kgrubb/oura-helm-chart/actions/workflows/ci.yml/badge.svg)](https://github.com/kgrubb/oura-helm-chart/actions/workflows/ci.yml)

Helm chart that syncs [Oura Ring](https://ouraring.com/) API v2 data into PostgreSQL.

## Install

```bash
helm repo add kgrubb-oura https://kgrubb.github.io/oura-helm-chart
helm repo update
helm install oura kgrubb-oura/oura -n monitoring --create-namespace \
  --set postgres.existingSecret=oura-db \
  --set auth.existingSecret=oura-api
```

Chart index: https://kgrubb.github.io/oura-helm-chart/

Published packages are signed. Verify with the [public key](https://kgrubb.github.io/oura-helm-chart/public.key) on gh-pages.

## Prerequisites

1. PostgreSQL database and login role (not created by the chart).
2. Secret with the database password (`postgres.existingSecret`).
3. Oura credentials Secret:
   - **Recommended:** personal access token (`auth.mode=pat`) from [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens).
   - **Alternative:** OAuth client id/secret plus token JSON on a PVC (`auth.mode=oauth`).

## Symptom Radar

After each sync the collector scores overnight biometrics into `symptom_radar_daily` (`none` / `minor` / `major`).

## OAuth scopes

For workouts, resilience, and cardiovascular age, authorize with:

```text
email personal daily heartrate spo2 workout stress heart_health
```

Enable the same scopes on the Oura API application.

## Grafana dashboard

Optional ConfigMap for the Grafana dashboard sidecar:

```yaml
dashboard:
  enabled: true
  datasourceUid: oura-postgres   # your Grafana Postgres datasource UID
```

## Example

```yaml
postgres:
  host: postgres-rw.postgres.svc.cluster.local
  database: oura
  user: oura
  existingSecret: oura-db

auth:
  mode: pat
  existingSecret: oura-api

schedule: "0 */6 * * *"
timeZone: America/New_York

dashboard:
  enabled: true
  datasourceUid: oura-postgres

backfill:
  enabled: true
  startDate: "2015-01-01"
```

## Releases

Pushes to `main` that change `charts/` bump the chart version from conventional commits (`feat:` minor, breaking major, otherwise patch), publish with [chart-releaser](https://github.com/helm/chart-releaser-action), and host packages on `gh-pages`.

## Development

```bash
helm lint charts/oura --strict -f ci/values.yaml
helm template test charts/oura -f ci/values.yaml
python3 tests/test_symptom_radar.py
```
