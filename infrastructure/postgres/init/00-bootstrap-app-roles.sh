#!/bin/sh
set -eu

: "${DB_APP_READ_USERNAME:?DB_APP_READ_USERNAME is required}"
: "${DB_APP_READ_PASSWORD:?DB_APP_READ_PASSWORD is required}"
: "${DB_APP_WRITE_USERNAME:?DB_APP_WRITE_USERNAME is required}"
: "${DB_APP_WRITE_PASSWORD:?DB_APP_WRITE_PASSWORD is required}"
: "${DB_APP_ADMIN_USERNAME:?DB_APP_ADMIN_USERNAME is required}"
: "${DB_APP_ADMIN_PASSWORD:?DB_APP_ADMIN_PASSWORD is required}"

psql \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set app_db="$POSTGRES_DB" \
  --set read_user="$DB_APP_READ_USERNAME" \
  --set read_password="$DB_APP_READ_PASSWORD" \
  --set write_user="$DB_APP_WRITE_USERNAME" \
  --set write_password="$DB_APP_WRITE_PASSWORD" \
  --set admin_user="$DB_APP_ADMIN_USERNAME" \
  --set admin_password="$DB_APP_ADMIN_PASSWORD" \
  -v ON_ERROR_STOP=1 <<'SQL'
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT',
    :'read_user',
    :'read_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'read_user') \gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'read_user', :'read_password') \gexec

SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT',
    :'write_user',
    :'write_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'write_user') \gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'write_user', :'write_password') \gexec

SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT',
    :'admin_user',
    :'admin_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'admin_user') \gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'admin_user', :'admin_password') \gexec

REVOKE ALL ON DATABASE :"app_db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"app_db" TO :"read_user";
GRANT CONNECT ON DATABASE :"app_db" TO :"write_user";
GRANT ALL PRIVILEGES ON DATABASE :"app_db" TO :"admin_user";
ALTER DATABASE :"app_db" OWNER TO :"admin_user";

COMMENT ON DATABASE :"app_db" IS
'Основная база персонального портфолио. Обслуживается bootstrap-superuser, app-read, app-write и app-admin ролями.';
SQL
