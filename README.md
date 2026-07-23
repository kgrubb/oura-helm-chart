# oura

Helm chart that syncs [Oura Ring](https://ouraring.com/) API v2 data into PostgreSQL for Grafana (or any SQL client).

## Install

```bash
helm repo add kgrubb-oura https://kgrubb.github.io/oura-helm-chart
helm repo update
helm install oura kgrubb-oura/oura -n monitoring --create-namespace \
  --set postgres.existingSecret=oura-db \
  --set auth.existingSecret=oura-api \
  --set auth.mode=pat
```

Chart index: https://kgrubb.github.io/oura-helm-chart/

Published charts are signed with the [public key](https://kgrubb.github.io/oura-helm-chart/public.key) on gh-pages.

## Prerequisites

1. PostgreSQL database + login role (chart does not provision the cluster).
2. Kubernetes Secret with the DB password (`postgres.existingSecret`).
3. Oura auth Secret:
   - **Recommended:** personal access token (`auth.mode=pat`) from [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens).
   - **Alternative:** OAuth client id/secret + token JSON on a PVC (`auth.mode=oauth`).

## Example values

```yaml
postgres:
  host: postgres-rw.postgres.svc.cluster.local
  database: oura
  user: oura
  existingSecret: oura-db
  passwordKey: password

auth:
  mode: pat
  existingSecret: oura-api
  patKey: OURA_PAT

schedule: "0 */6 * * *"
timeZone: America/New_York

backfill:
  enabled: true
  startDate: "2015-01-01"
```

## Releases

Pushes to `main` that change `charts/` bump the chart version from conventional commits (`feat:` minor, breaking major, otherwise patch), publish with [chart-releaser](https://github.com/helm/chart-releaser-action), and host `index.yaml` plus packages on `gh-pages`.

## Development

```bash
helm lint charts/oura --strict
helm template test charts/oura \
  --set postgres.existingSecret=oura-db \
  --set auth.existingSecret=oura-api
```
