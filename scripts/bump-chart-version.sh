#!/usr/bin/env bash
set -euo pipefail

CHART_FILE="charts/oura/Chart.yaml"
BEFORE_SHA="${1:?before sha required}"
AFTER_SHA="${2:?after sha required}"

current_version=$(awk '/^version:/ { print $2; exit }' "$CHART_FILE")

bump_level="patch"
breaking_re='^[a-zA-Z]+(\([^)]+\))?!:'
feat_re='^feat(\([^)]+\))?:'

while IFS= read -r -d '' message; do
  subject=${message%%$'\n'*}
  [[ -z "$subject" || "$subject" =~ ^chore\(release\): ]] && continue

  if [[ "$subject" =~ $breaking_re ]] || [[ "$message" == *"BREAKING CHANGE"* ]]; then
    bump_level="major"
    break
  fi
  if [[ "$subject" =~ $feat_re ]] && [[ "$bump_level" != "major" ]]; then
    bump_level="minor"
  fi
done < <(git log -z --format=%B "${BEFORE_SHA}..${AFTER_SHA}")

IFS='.' read -r major minor patch <<< "$current_version"
case "$bump_level" in
  major) major=$((major + 1)); minor=0; patch=0 ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  patch) patch=$((patch + 1)) ;;
esac

new_version="${major}.${minor}.${patch}"
[[ "$new_version" == "$current_version" ]] && exit 0

./scripts/versions.sh set "$new_version"
echo "Bumped ${current_version} -> ${new_version} (${bump_level})"
