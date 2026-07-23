# oura

CronJob that loads Oura Ring API v2 into PostgreSQL (daily metrics, sleep periods/stages, heart rate).

## Values

| Key | Default | Notes |
| --- | --- | --- |
| `image.repository` | `ghcr.io/astral-sh/uv` | Runtime image (`python3.12-alpine` tag) |
| `schedule` | `0 */6 * * *` | Cron expression |
| `timeZone` | `UTC` | CronJob `timeZone` |
| `recentDays` | `14` | Trailing days re-fetched every run |
| `postgres.host` | `postgres` | PostgreSQL hostname |
| `postgres.existingSecret` | `""` | **Required.** DB password Secret |
| `auth.mode` | `pat` | `pat` or `oauth` |
| `auth.existingSecret` | `""` | **Required.** Oura credentials Secret |
| `persistence.enabled` | `true` | Token PVC when `auth.mode=oauth` |
| `backfill.enabled` | `false` | One-shot historical Job |
| `dashboard.enabled` | `false` | Grafana sidecar dashboard ConfigMap |
| `dashboard.datasourceUid` | `oura-postgres` | Grafana Postgres datasource UID |
| `resources` | modest defaults | Override per environment |

The collector also writes **Symptom Radar** results into `symptom_radar_daily`.

Provision the database and roles outside the chart. Grant Grafana a read-only role separately.

See [values.yaml](values.yaml) and the [Oura API v2 docs](https://cloud.ouraring.com/v2/docs).
