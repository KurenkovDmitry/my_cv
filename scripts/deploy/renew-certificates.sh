#!/bin/sh
set -eu

DEPLOY_ROOT="${1:-/opt/portfolio}"
CURRENT_RELEASE_DIR="${DEPLOY_ROOT}/app/current"
ENV_FILE="${CURRENT_RELEASE_DIR}/.env"
COMPOSE_FILE="${CURRENT_RELEASE_DIR}/docker-compose.production.yml"

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

if [ ! -d "${CURRENT_RELEASE_DIR}" ] || [ ! -f "${ENV_FILE}" ] || [ ! -f "${COMPOSE_FILE}" ]; then
  echo "Current release is not ready for certificate renewal." >&2
  exit 1
fi

set -a
. "${ENV_FILE}"
set +a

export COMPOSE_PROJECT_NAME=portfolio
export IMAGE_TAG="${IMAGE_TAG:-current}"

run_root docker compose \
  --env-file "${ENV_FILE}" \
  -f "${COMPOSE_FILE}" \
  run --rm certbot renew --webroot -w /var/www/certbot --quiet

run_root docker compose \
  --env-file "${ENV_FILE}" \
  -f "${COMPOSE_FILE}" \
  exec -T nginx nginx -s reload
