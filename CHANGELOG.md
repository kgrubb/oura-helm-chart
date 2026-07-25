# Changelog

All notable changes to this chart are documented here.

## [Unreleased]

## [1.0.0] - 2026-07-25

### Added
- Versioned collector image (`ghcr.io/kgrubb/oura-collector`) built and published in release CI ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Optional quickstart that creates Secrets, bootstraps Postgres roles, and enables the Grafana dashboard and datasource ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Optional Postgres bootstrap hook Job ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Helm unit tests and Python packaging (`uv`, ruff, pytest) ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))

### Changed
- Collector runs from the container image instead of ConfigMap Python on the `uv` image ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Chart defaults, helpers, and docs for Secret-based and quickstart installs ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Release and CI pipelines target Helm 4 ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Release pipeline keeps chart version, appVersion, image tag, and pyproject version aligned ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Release makes the GHCR collector package public after push and verifies visibility before chart publish ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Postgres bootstrap runs as a `pre-install` / `pre-upgrade` hook so DB roles exist before CronJob or backfill Jobs start ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Read-only Postgres role is opt-in (`postgres.bootstrap.readOnlyUser`). Quickstart defaults to `oura_ro` only when the chart creates the DB Secret ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Bootstrap does not rotate passwords on existing roles (avoids Secret / DB desync during upgrades) ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Set `image.repository=ghcr.io/kgrubb/oura-collector` and `image.tag=` (empty) when upgrading from 0.x with reused values ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Existing Secret and OAuth installs keep working. Leave `quickstart.enabled` and `dashboard.createDatasource` off if you already manage those ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))

### Fixed
- Schema grants to `oura_ro` only when that role exists, so collector startup no longer races bootstrap ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Validation rejects reused pre-1.0 `uv` / `python3.12-alpine` image overrides on upgrade ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Bootstrap Job takes chart-managed credentials from values so DB Secrets stay regular resources ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Bootstrap with an existing DB Secret no longer requires a `password-ro` key unless `readOnlyUser` is set ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- `dashboard.createDatasource` no longer uses Helm `lookup`, so GitOps / `helm template` works. Set `dashboard.datasource.password` when using `postgres.existingSecret` ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))
- Bootstrap Job does not depend on the chart ServiceAccount, so enabling bootstrap later cannot break SA ownership ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))

### Removed
- ConfigMap-shipped `collector.py` / `symptom_radar.py` runtime ([#1](https://github.com/kgrubb/oura-helm-chart/pull/1))



## [0.2.10] - 2026-07-24

### Fixed
- default collector schedule to every 15 minutes



## [0.2.9] - 2026-07-23

### Fixed
- polish Oura dashboard UX and score radar on readiness day



## [0.2.8] - 2026-07-23

### Fixed
- calibrate Symptom Radar v3 and rename to no signs



## [0.2.7] - 2026-07-23

### Fixed
- make Symptom Radar conservative (v2) and clarify dashboard.



## [0.2.6] - 2026-07-23

### Changed
- backfill real changelog entries for all chart releases.



## [0.2.5] - 2026-07-23

### Fixed
- Use correct Oura API path casing for VO2 max (`vO2_max`)

## [0.2.4] - 2026-07-23

### Fixed
- Symptom Radar stat panel shows status instead of "No data" (numeric mappings)
- Radar Details and workout tables use readable dates (`Mon D`)
- Stress and Resilience stats use readable status labels

### Changed
- Rename readiness breakdown panel to Readiness factors with plain labels
- Document OAuth scopes needed for workouts, resilience, and cardiovascular age
- Slim collector code

## [0.2.3] - 2026-07-23

### Changed
- Align Symptom Radar status label casing with the dashboard

## [0.2.2] - 2026-07-23

### Changed
- Symptom Radar title and labels are end-user facing (no algorithm/proxy wording)
- Radar Details shows day and status only
- Drop k3s-specific wording from chart docs and templates

## [0.2.1] - 2026-07-23

### Fixed
- Keep OAuth token PVC across helm uninstall/reinstall (`helm.sh/resource-policy: keep`)

## [0.2.0] - 2026-07-23

### Added
- Symptom Radar daily scoring into `symptom_radar_daily`
- Sync resilience, workout, cardiovascular age, VO2 max, and sleep time
- Activity zone columns on `daily_activity` (sedentary/low/medium/high)
- Optional Grafana dashboard ConfigMap (`dashboard.enabled`)
- Unit tests for Symptom Radar scoring

## [0.1.2] - 2026-07-23

### Fixed
- Enable Artifact Hub schema, chart signing, and verification metadata

## [0.1.1] - 2026-07-23

### Changed
- Docs: drop arrows, em dashes, and semicolon prose

## [0.1.0] - 2026-07-23

### Added
- Initial Oura Ring → PostgreSQL Helm chart (CronJob collector, PAT or OAuth, optional backfill)

### Fixed
- Make CI and first release reliable
