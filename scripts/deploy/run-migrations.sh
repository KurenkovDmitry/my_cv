#!/bin/sh
set -eu

: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_PORT:?POSTGRES_PORT is required}"
: "${POSTGRES_DB_NAME:?POSTGRES_DB_NAME is required}"
: "${DB_APP_ADMIN_USERNAME:?DB_APP_ADMIN_USERNAME is required}"
: "${DB_APP_ADMIN_PASSWORD:?DB_APP_ADMIN_PASSWORD is required}"

export PGPASSWORD="${DB_APP_ADMIN_PASSWORD}"

until pg_isready \
  --host "${POSTGRES_HOST}" \
  --port "${POSTGRES_PORT}" \
  --username "${DB_APP_ADMIN_USERNAME}" \
  --dbname "${POSTGRES_DB_NAME}" >/dev/null 2>&1; do
  sleep 2
done

psql \
  --host "${POSTGRES_HOST}" \
  --port "${POSTGRES_PORT}" \
  --username "${DB_APP_ADMIN_USERNAME}" \
  --dbname "${POSTGRES_DB_NAME}" \
  -v ON_ERROR_STOP=1 \
  -f /app/backend/migrations/sql/0001_initial_schema.sql

/app/scripts/postgres/refresh-app-grants.sh
