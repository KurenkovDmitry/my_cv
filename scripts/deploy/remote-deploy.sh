#!/bin/sh
set -eu

DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/portfolio}"
RELEASE_SHA="${RELEASE_SHA:?RELEASE_SHA is required}"
DEPLOY_SERVER_ID="${DEPLOY_SERVER_ID:?DEPLOY_SERVER_ID is required}"
TARGET_DOMAIN_NAME="${TARGET_DOMAIN_NAME:?TARGET_DOMAIN_NAME is required}"
TARGET_LETSENCRYPT_EMAIL="${TARGET_LETSENCRYPT_EMAIL:-}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-false}"
BUNDLE_ARCHIVE="${BUNDLE_ARCHIVE:-/tmp/portfolio-deploy-bundle-${RELEASE_SHA}.tar.gz}"
API_IMAGE_ARCHIVE="${API_IMAGE_ARCHIVE:-/tmp/portfolio-api-${RELEASE_SHA}.tar.gz}"
NGINX_IMAGE_ARCHIVE="${NGINX_IMAGE_ARCHIVE:-/tmp/portfolio-web-nginx-${RELEASE_SHA}.tar.gz}"
ENV_ARCHIVE="${ENV_ARCHIVE:-/tmp/portfolio-production.env}"

RELEASE_DIR="${DEPLOY_ROOT}/app/releases/${RELEASE_SHA}"
CURRENT_RELEASE_LINK="${DEPLOY_ROOT}/app/current"
ENV_FILE="${DEPLOY_ROOT}/config/.env"
SERVER_ID_FILE="/etc/portfolio/deploy-server-id"

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi

run_root() {
  if [ -n "${SUDO}" ]; then
    ${SUDO} "$@"
  else
    "$@"
  fi
}

docker_compose() {
  if [ -n "${SUDO}" ]; then
    ${SUDO} docker compose --env-file "${RELEASE_DIR}/.env" -f "${RELEASE_DIR}/docker-compose.production.yml" "$@"
  else
    docker compose --env-file "${RELEASE_DIR}/.env" -f "${RELEASE_DIR}/docker-compose.production.yml" "$@"
  fi
}

wait_for_http() {
  target_url="$1"
  shift

  attempt=1
  while [ "${attempt}" -le 30 ]; do
    if curl --fail --silent --show-error "$@" "${target_url}" >/dev/null 2>&1; then
      return 0
    fi

    attempt=$((attempt + 1))
    sleep 3
  done

  echo "Timed out while waiting for ${target_url}." >&2
  return 1
}

ensure_server_identity() {
  if run_root test -f "${SERVER_ID_FILE}"; then
    current_server_id="$(run_root cat "${SERVER_ID_FILE}")"
    if [ "${current_server_id}" != "${DEPLOY_SERVER_ID}" ]; then
      echo "Server identity mismatch. Refusing to deploy." >&2
      exit 1
    fi
    return
  fi

  if [ "${BOOTSTRAP_SERVER}" != "true" ]; then
    echo "Server identity file is missing. Run the first deploy in bootstrap mode." >&2
    exit 1
  fi

  printf '%s' "${DEPLOY_SERVER_ID}" | run_root tee "${SERVER_ID_FILE}" >/dev/null
  run_root chmod 600 "${SERVER_ID_FILE}"
}

export COMPOSE_PROJECT_NAME=portfolio

run_root mkdir -p "${DEPLOY_ROOT}/app/releases" "${DEPLOY_ROOT}/config" "${DEPLOY_ROOT}/tmp" /etc/portfolio
run_root rm -rf "${RELEASE_DIR}"
run_root mkdir -p "${RELEASE_DIR}"
run_root tar -xzf "${BUNDLE_ARCHIVE}" -C "${RELEASE_DIR}"
run_root chmod +x "${RELEASE_DIR}/scripts/deploy/"*.sh "${RELEASE_DIR}/scripts/postgres/"*.sh

ensure_server_identity
sh "${RELEASE_DIR}/scripts/deploy/bootstrap-server.sh" "${DEPLOY_ROOT}"

run_root sh -c "tr -d '\r' < '${ENV_ARCHIVE}' > '${ENV_FILE}'"
run_root chmod 600 "${ENV_FILE}"
run_root ln -sfn "${ENV_FILE}" "${RELEASE_DIR}/.env"

set -a
. "${RELEASE_DIR}/.env"
set +a

if [ "${DOMAIN_NAME}" != "${TARGET_DOMAIN_NAME}" ]; then
  echo "DOMAIN_NAME inside .env does not match the expected production domain." >&2
  exit 1
fi

if [ -z "${TARGET_LETSENCRYPT_EMAIL}" ]; then
  echo "TARGET_LETSENCRYPT_EMAIL is required for HTTPS deployment." >&2
  exit 1
fi

run_root sh -c "gunzip -c '${API_IMAGE_ARCHIVE}' | docker load"
run_root sh -c "gunzip -c '${NGINX_IMAGE_ARCHIVE}' | docker load"
run_root docker tag "portfolio-api:${RELEASE_SHA}" portfolio-api:current
run_root docker tag "portfolio-web-nginx:${RELEASE_SHA}" portfolio-web-nginx:current

docker_compose up -d postgres redis

attempt=1
while [ "${attempt}" -le 30 ]; do
  if docker_compose exec -T postgres pg_isready -U "${POSTGRES_SUPERUSER_NAME}" -d "${POSTGRES_DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 3
done

if [ "${attempt}" -gt 30 ]; then
  echo "PostgreSQL did not become ready in time." >&2
  exit 1
fi

docker_compose exec -T postgres sh /docker-entrypoint-initdb.d/00-bootstrap-app-roles.sh
docker_compose run --rm api sh /app/scripts/deploy/run-migrations.sh

ENABLE_HTTPS=false docker_compose up -d api nginx
wait_for_http "http://127.0.0.1:8000/health/live"

ENABLE_HTTPS=false docker_compose run --rm certbot certonly \
  --webroot \
  -w /var/www/certbot \
  --agree-tos \
  --no-eff-email \
  --non-interactive \
  --keep-until-expiring \
  --email "${TARGET_LETSENCRYPT_EMAIL}" \
  --cert-name "${TARGET_DOMAIN_NAME}" \
  -d "${TARGET_DOMAIN_NAME}"

ENABLE_HTTPS=true docker_compose up -d api nginx
wait_for_http "https://${TARGET_DOMAIN_NAME}/" --resolve "${TARGET_DOMAIN_NAME}:443:127.0.0.1"

run_root ln -sfn "${RELEASE_DIR}" "${CURRENT_RELEASE_LINK}"
sh "${RELEASE_DIR}/scripts/deploy/install-cert-renew-timer.sh" "${DEPLOY_ROOT}"

run_root rm -f "${BUNDLE_ARCHIVE}" "${API_IMAGE_ARCHIVE}" "${NGINX_IMAGE_ARCHIVE}" "${ENV_ARCHIVE}"
