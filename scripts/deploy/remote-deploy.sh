#!/bin/sh
set -eu

DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/portfolio}"
RELEASE_SHA="${RELEASE_SHA:?RELEASE_SHA is required}"
DEPLOY_SERVER_ID="${DEPLOY_SERVER_ID:?DEPLOY_SERVER_ID is required}"
TARGET_DOMAIN_NAME="${TARGET_DOMAIN_NAME:?TARGET_DOMAIN_NAME is required}"
TARGET_LETSENCRYPT_EMAIL="${TARGET_LETSENCRYPT_EMAIL:-}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-false}"
RECREATE_STATEFUL_SERVICES="${RECREATE_STATEFUL_SERVICES:-false}"
RUN_DATABASE_MAINTENANCE="${RUN_DATABASE_MAINTENANCE:-false}"
BUNDLE_ARCHIVE="${BUNDLE_ARCHIVE:-/tmp/portfolio-deploy-bundle-${RELEASE_SHA}.tar.gz}"
API_IMAGE_ARCHIVE="${API_IMAGE_ARCHIVE:-/tmp/portfolio-api-${RELEASE_SHA}.tar.gz}"
NGINX_IMAGE_ARCHIVE="${NGINX_IMAGE_ARCHIVE:-/tmp/portfolio-web-nginx-${RELEASE_SHA}.tar.gz}"
ENV_ARCHIVE="${ENV_ARCHIVE:-/tmp/portfolio-production.env}"

RELEASE_DIR="${DEPLOY_ROOT}/app/releases/${RELEASE_SHA}"
CURRENT_RELEASE_LINK="${DEPLOY_ROOT}/app/current"
ATTEMPT_RELEASE_LINK="${DEPLOY_ROOT}/app/last_attempt"
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

CURRENT_STEP="initializing"

log_step() {
  CURRENT_STEP="$1"
  printf '\n==> %s\n' "${CURRENT_STEP}"
}

update_release_link() {
  link_path="$1"
  target_path="$2"

  if run_root test -d "${link_path}" && ! run_root test -L "${link_path}"; then
    run_root rm -rf "${link_path}"
  fi

  run_root ln -sfn "${target_path}" "${link_path}"
}

cleanup_release_directories() {
  if [ ! -d "${DEPLOY_ROOT}/app/releases" ]; then
    return
  fi

  run_root find "${DEPLOY_ROOT}/app/releases" -mindepth 1 -maxdepth 1 -type d ! -name "${RELEASE_SHA}" -exec rm -rf {} +
}

cleanup_repository_image_tags() {
  repository="$1"
  keep_primary_tag="$2"
  keep_secondary_tag="$3"

  image_refs="$(run_root docker image ls "${repository}" --format '{{.Repository}}:{{.Tag}}')"
  if [ -z "${image_refs}" ]; then
    return
  fi

  echo "${image_refs}" | while IFS= read -r image_ref; do
    [ -z "${image_ref}" ] && continue

    case "${image_ref}" in
      "${repository}:${keep_primary_tag}"|"${repository}:${keep_secondary_tag}"|"${repository}:<none>")
        continue
        ;;
    esac

    run_root docker image rm "${image_ref}" >/dev/null 2>&1 || true
  done
}

cleanup_runtime_artifacts() {
  cleanup_release_directories
  cleanup_repository_image_tags "portfolio-api" "current" "${RELEASE_SHA}"
  cleanup_repository_image_tags "portfolio-web-nginx" "current" "${RELEASE_SHA}"
  run_root docker image prune -f >/dev/null 2>&1 || true
}

sync_environment_files() {
  tr -d '\r' < "${ENV_ARCHIVE}" > "${RELEASE_DIR}/.env"
  printf '\nIMAGE_TAG=%s\n' "${RELEASE_SHA}" >> "${RELEASE_DIR}/.env"
  chmod 600 "${RELEASE_DIR}/.env"

  run_root cp "${RELEASE_DIR}/.env" "${ENV_FILE}"
  run_root chmod 600 "${ENV_FILE}"

  if [ -n "${SUDO}" ]; then
    run_root chown "$(id -u)":"$(id -g)" "${ENV_FILE}"
  fi
}

docker_compose() {
  compose_project_name="${COMPOSE_PROJECT_NAME:-portfolio}"
  compose_image_tag="${IMAGE_TAG:-$RELEASE_SHA}"
  compose_enable_https="${ENABLE_HTTPS:-}"

  if [ -n "${SUDO}" ]; then
    ${SUDO} env \
      COMPOSE_PROJECT_NAME="${compose_project_name}" \
      IMAGE_TAG="${compose_image_tag}" \
      ENABLE_HTTPS="${compose_enable_https}" \
      docker compose --env-file "${RELEASE_DIR}/.env" -f "${RELEASE_DIR}/docker-compose.production.yml" "$@"
  else
    env \
      COMPOSE_PROJECT_NAME="${compose_project_name}" \
      IMAGE_TAG="${compose_image_tag}" \
      ENABLE_HTTPS="${compose_enable_https}" \
      docker compose --env-file "${RELEASE_DIR}/.env" -f "${RELEASE_DIR}/docker-compose.production.yml" "$@"
  fi
}

docker_compose_exec_no_stdin() {
  docker_compose exec -T "$@" </dev/null
}

docker_compose_run_no_stdin() {
  docker_compose run --rm "$@" </dev/null
}

should_run_database_maintenance() {
  if [ "${BOOTSTRAP_SERVER}" = "true" ] || [ "${RECREATE_STATEFUL_SERVICES}" = "true" ]; then
    return 0
  fi

  [ "${RUN_DATABASE_MAINTENANCE}" = "true" ]
}

replace_services() {
  compose_enable_https="$1"
  shift

  ENABLE_HTTPS="${compose_enable_https}" docker_compose rm -f -s "$@" || true
  ENABLE_HTTPS="${compose_enable_https}" docker_compose up -d --force-recreate --remove-orphans --no-deps "$@"
}

debug_on_error() {
  exit_code="$1"

  echo "Deployment failed during step: ${CURRENT_STEP}" >&2

  if command -v docker >/dev/null 2>&1; then
    echo "--- docker compose ps ---" >&2
    docker_compose ps >&2 || true

    echo "--- api logs ---" >&2
    docker_compose logs --tail=80 api >&2 || true

    echo "--- grafana logs ---" >&2
    docker_compose logs --tail=80 grafana >&2 || true

    echo "--- nginx logs ---" >&2
    docker_compose logs --tail=80 nginx >&2 || true
  fi

  exit "${exit_code}"
}

trap 'exit_code="$?"; if [ "${exit_code}" -ne 0 ]; then debug_on_error "${exit_code}"; fi' EXIT
trap 'exit 130' INT TERM HUP

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

wait_for_internal_http() {
  source_service="$1"
  target_url="$2"
  attempt=1

  while [ "${attempt}" -le 30 ]; do
    if docker_compose_exec_no_stdin "${source_service}" \
      curl --fail --silent --show-error "${target_url}" >/dev/null 2>&1; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 3
  done

  echo "Timed out while waiting for ${target_url} from ${source_service}." >&2
  return 1
}

describe_service_container() {
  service_name="$1"
  container_id="$(docker_compose ps -q "${service_name}" | head -n 1)"

  if [ -z "${container_id}" ]; then
    echo "Service ${service_name} container not found after deploy." >&2
    return 1
  fi

  run_root docker inspect \
    --format "service=${service_name} id={{.Id}} name={{.Name}} image={{.Config.Image}} status={{.State.Status}} started_at={{.State.StartedAt}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" \
    "${container_id}"
}

verify_deployed_release() {
  expected_api_image="portfolio-api:${RELEASE_SHA}"
  expected_nginx_image="portfolio-web-nginx:${RELEASE_SHA}"

  api_container_id="$(docker_compose ps -q api | head -n 1)"
  grafana_container_id="$(docker_compose ps -q grafana | head -n 1)"
  nginx_container_id="$(docker_compose ps -q nginx | head -n 1)"

  if [ -z "${api_container_id}" ] || [ -z "${grafana_container_id}" ] || [ -z "${nginx_container_id}" ]; then
    echo "api, grafana or nginx container is missing after deploy." >&2
    return 1
  fi

  api_config_image="$(run_root docker inspect --format '{{.Config.Image}}' "${api_container_id}")"
  nginx_config_image="$(run_root docker inspect --format '{{.Config.Image}}' "${nginx_container_id}")"

  if [ "${api_config_image}" != "${expected_api_image}" ]; then
    echo "api container runs unexpected image: ${api_config_image} (expected ${expected_api_image})." >&2
    return 1
  fi

  if [ "${nginx_config_image}" != "${expected_nginx_image}" ]; then
    echo "nginx container runs unexpected image: ${nginx_config_image} (expected ${expected_nginx_image})." >&2
    return 1
  fi

  echo "--- deployed container snapshot ---"
  describe_service_container api
  describe_service_container grafana
  describe_service_container nginx
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

log_step "Preparing release directory"
run_root mkdir -p "${DEPLOY_ROOT}/app/releases" "${DEPLOY_ROOT}/config" "${DEPLOY_ROOT}/tmp" /etc/portfolio
run_root rm -rf "${RELEASE_DIR}"
run_root mkdir -p "${RELEASE_DIR}"
run_root tar -xzf "${BUNDLE_ARCHIVE}" -C "${RELEASE_DIR}"
update_release_link "${ATTEMPT_RELEASE_LINK}" "${RELEASE_DIR}"
run_root chmod +x "${RELEASE_DIR}/scripts/deploy/"*.sh "${RELEASE_DIR}/scripts/postgres/"*.sh

log_step "Validating server identity and bootstrap"
ensure_server_identity
sh "${RELEASE_DIR}/scripts/deploy/bootstrap-server.sh" "${DEPLOY_ROOT}"

log_step "Syncing environment"
sync_environment_files

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

log_step "Validating deployment configuration"
docker_compose config --quiet

log_step "Loading release images"
run_root sh -c "gunzip -c '${API_IMAGE_ARCHIVE}' | docker load"
run_root sh -c "gunzip -c '${NGINX_IMAGE_ARCHIVE}' | docker load"
run_root docker tag "portfolio-api:${RELEASE_SHA}" portfolio-api:current
run_root docker tag "portfolio-web-nginx:${RELEASE_SHA}" portfolio-web-nginx:current

log_step "Preparing runtime service images"
docker_compose pull grafana certbot

if should_run_database_maintenance; then
  log_step "Starting stateful services"
  if [ "${RECREATE_STATEFUL_SERVICES}" = "true" ]; then
    docker_compose up -d --force-recreate postgres redis
  else
    docker_compose up -d --no-recreate postgres redis
  fi

  log_step "Waiting for PostgreSQL"
  attempt=1
  while [ "${attempt}" -le 30 ]; do
    if docker_compose_exec_no_stdin postgres pg_isready -U "${POSTGRES_SUPERUSER_NAME}" -d "${POSTGRES_DB_NAME}" >/dev/null 2>&1; then
      break
    fi
    attempt=$((attempt + 1))
    sleep 3
  done

  if [ "${attempt}" -gt 30 ]; then
    echo "PostgreSQL did not become ready in time." >&2
    exit 1
  fi

  log_step "Applying database grants"
  docker_compose_exec_no_stdin postgres sh /docker-entrypoint-initdb.d/00-bootstrap-app-roles.sh

  log_step "Running database migrations"
  docker_compose_run_no_stdin api sh /app/scripts/deploy/run-migrations.sh
else
  log_step "Skipping database maintenance"
  echo "Stateful services are left untouched. Deploying api, grafana and nginx against the existing PostgreSQL/Redis instances."
fi

log_step "Deploying application over HTTP"
replace_services false api grafana
wait_for_http "http://127.0.0.1:8000/health/live"
wait_for_http "http://127.0.0.1:8000/api/public/portfolio"
wait_for_http "http://127.0.0.1:8000/api/public/portfolio/social-meta"
wait_for_http "http://127.0.0.1:8000/api/public/portfolio/social-preview"
wait_for_http "http://127.0.0.1:8000/api/public/portfolio/favicon"
wait_for_internal_http api "http://grafana:3000/api/health"
replace_services false nginx
wait_for_http "http://127.0.0.1/"

log_step "Issuing or renewing TLS certificate"
ENABLE_HTTPS=false docker_compose_run_no_stdin certbot certonly \
  --webroot \
  -w /var/www/certbot \
  --agree-tos \
  --no-eff-email \
  --non-interactive \
  --keep-until-expiring \
  --email "${TARGET_LETSENCRYPT_EMAIL}" \
  --cert-name "${TARGET_DOMAIN_NAME}" \
  -d "${TARGET_DOMAIN_NAME}"

log_step "Deploying application over HTTPS"
replace_services true nginx
wait_for_http "https://${TARGET_DOMAIN_NAME}/" --resolve "${TARGET_DOMAIN_NAME}:443:127.0.0.1"
verify_deployed_release

log_step "Finalizing release"
update_release_link "${CURRENT_RELEASE_LINK}" "${RELEASE_DIR}"
sh "${RELEASE_DIR}/scripts/deploy/install-cert-renew-timer.sh" "${DEPLOY_ROOT}"
cleanup_runtime_artifacts

run_root rm -f "${BUNDLE_ARCHIVE}" "${API_IMAGE_ARCHIVE}" "${NGINX_IMAGE_ARCHIVE}" "${ENV_ARCHIVE}"
