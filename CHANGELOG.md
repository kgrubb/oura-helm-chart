# Changelog

All notable changes to this chart are documented here.

## [Unreleased]

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
