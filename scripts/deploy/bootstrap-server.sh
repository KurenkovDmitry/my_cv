#!/bin/sh
set -eu

DEPLOY_ROOT="${1:-/opt/portfolio}"

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

if command -v apt-get >/dev/null 2>&1; then
  run_root apt-get update
  run_root apt-get install -y ca-certificates curl rsync openssl
else
  echo "Only apt-based Linux distributions are supported by bootstrap-server.sh." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | run_root sh
fi

run_root systemctl enable --now docker

run_root mkdir -p \
  "${DEPLOY_ROOT}/app/releases" \
  "${DEPLOY_ROOT}/config" \
  "${DEPLOY_ROOT}/tmp" \
  "${DEPLOY_ROOT}/backups" \
  /etc/portfolio

if [ -n "${SUDO}" ]; then
  run_root chown -R "$(id -u)":"$(id -g)" "${DEPLOY_ROOT}/app" "${DEPLOY_ROOT}/config" "${DEPLOY_ROOT}/tmp"
fi
