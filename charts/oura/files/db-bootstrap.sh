#!/bin/sh
# Create database, write role, and optional read-only role (safe to re-run).
set -eu

ident_ok() {
  # Allow only plain SQL identifiers.
  case "$1" in
    '' | *[!a-zA-Z0-9_]* | [0-9]*)
      echo "invalid SQL identifier: $1" >&2
      return 1
      ;;
  esac
}

esc_literal() {
  printf "%s" "$1" | sed "s/'/''/g"
}

: "${PGHOST:?}"
: "${PGPORT:?}"
: "${PGUSER:?}"
: "${PGPASSWORD:?}"
: "${OURA_DB:?}"
: "${OURA_USER:?}"
: "${OURA_DB_PASSWORD:?}"

ident_ok "$OURA_DB"
ident_ok "$OURA_USER"
PW=$(esc_literal "$OURA_DB_PASSWORD")

psql -v ON_ERROR_STOP=1 <<SQL
SELECT format('CREATE DATABASE %I', '${OURA_DB}')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${OURA_DB}')\gexec
DO \$\$
BEGIN
  CREATE ROLE ${OURA_USER} LOGIN PASSWORD '${PW}';
EXCEPTION WHEN duplicate_object THEN
  ALTER ROLE ${OURA_USER} WITH LOGIN PASSWORD '${PW}';
END
\$\$;
ALTER DATABASE ${OURA_DB} OWNER TO ${OURA_USER};
GRANT ALL PRIVILEGES ON DATABASE ${OURA_DB} TO ${OURA_USER};
SQL

psql -v ON_ERROR_STOP=1 -d "$OURA_DB" <<SQL
GRANT USAGE, CREATE ON SCHEMA public TO ${OURA_USER};
ALTER SCHEMA public OWNER TO ${OURA_USER};
SQL

if [ -n "${OURA_RO_USER:-}" ]; then
  : "${OURA_DB_RO_PASSWORD:?OURA_DB_RO_PASSWORD is required when OURA_RO_USER is set}"
  ident_ok "$OURA_RO_USER"
  PWRO=$(esc_literal "$OURA_DB_RO_PASSWORD")

  psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  CREATE ROLE ${OURA_RO_USER} LOGIN PASSWORD '${PWRO}';
EXCEPTION WHEN duplicate_object THEN
  ALTER ROLE ${OURA_RO_USER} WITH LOGIN PASSWORD '${PWRO}';
END
\$\$;
GRANT CONNECT ON DATABASE ${OURA_DB} TO ${OURA_RO_USER};
SQL

  psql -v ON_ERROR_STOP=1 -d "$OURA_DB" <<SQL
GRANT USAGE ON SCHEMA public TO ${OURA_RO_USER};
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${OURA_RO_USER};
ALTER DEFAULT PRIVILEGES FOR ROLE ${OURA_USER} IN SCHEMA public
  GRANT SELECT ON TABLES TO ${OURA_RO_USER};
SQL
fi

echo "oura db bootstrap ok"
