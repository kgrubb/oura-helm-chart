#!/usr/bin/env bash
# Keep chart version, appVersion, Artifact Hub image tag, and pyproject version aligned.
# Usage: versions.sh set <semver> | versions.sh check
set -euo pipefail

CMD="${1:?usage: versions.sh set <semver>|check}"
CHART_FILE="${CHART_FILE:-charts/oura/Chart.yaml}"
PYPROJECT_FILE="${PYPROJECT_FILE:-pyproject.toml}"
IMAGE_REPO="${IMAGE_REPO:-ghcr.io/kgrubb/oura-collector}"

chart_version() { awk '/^version:/ { print $2; exit }' "$CHART_FILE"; }
app_version() { awk '/^appVersion:/ { gsub(/"/, "", $2); print $2; exit }' "$CHART_FILE"; }
py_version() { awk '/^version = / { gsub(/"/, "", $3); print $3; exit }' "$PYPROJECT_FILE"; }
image_tag() {
  awk -v repo="$IMAGE_REPO" '
    $0 ~ "image: " repo ":" {
      sub(/.*:/, "")
      gsub(/[[:space:]]/, "")
      print
      exit
    }
  ' "$CHART_FILE"
}

set_version() {
  local version="$1"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-].*)?$ ]] || {
    echo "invalid version: $version" >&2
    exit 1
  }
  sed -i "s/^version: .*/version: ${version}/" "$CHART_FILE"
  sed -i "s/^appVersion: .*/appVersion: \"${version}\"/" "$CHART_FILE"
  sed -i "s|image: ${IMAGE_REPO}:[^[:space:]]*|image: ${IMAGE_REPO}:${version}|" "$CHART_FILE"
  if ! command -v uv >/dev/null 2>&1 || ! uv version "$version" >/dev/null 2>&1; then
    awk -v ver="$version" '
      BEGIN { done=0 }
      /^version = / && !done { sub(/"[^"]+"/, "\"" ver "\""); done=1 }
      { print }
    ' "$PYPROJECT_FILE" > "${PYPROJECT_FILE}.tmp"
    mv "${PYPROJECT_FILE}.tmp" "$PYPROJECT_FILE"
  fi
  echo "version set to ${version}"
}

check_versions() {
  local chart app image py fail=0 name value
  chart=$(chart_version)
  app=$(app_version)
  image=$(image_tag)
  py=$(py_version)
  for pair in "appVersion:${app}" "artifacthub image:${image}" "pyproject:${py}"; do
    name=${pair%%:*}
    value=${pair#*:}
    if [[ "$value" != "$chart" ]]; then
      echo "version mismatch: chart=${chart} ${name}=${value}" >&2
      fail=1
    fi
  done
  if [[ "$fail" -ne 0 ]]; then
    echo "run: ./scripts/versions.sh set ${chart}" >&2
    exit 1
  fi
  echo "versions aligned at ${chart}"
}

case "$CMD" in
  set) set_version "${2:?usage: versions.sh set <semver>}" ;;
  check) check_versions ;;
  *)
    echo "usage: versions.sh set <semver>|check" >&2
    exit 1
    ;;
esac
