#!/bin/sh
set -eu

DEPLOY_ROOT="${1:-/opt/portfolio}"

require_command() {
  command -v "$1" >/dev/null 2>&1
}

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  if ! require_command sudo; then
    echo "sudo is required when bootstrap-server.sh is not run as root." >&2
    exit 1
  fi

  SUDO="sudo"
fi

run_root() {
  if [ -n "${SUDO}" ]; then
    ${SUDO} "$@"
  else
    "$@"
  fi
}

install_prerequisites() {
  if require_command apt-get; then
    run_root apt-get update
    run_root apt-get install -y ca-certificates curl rsync openssl
    return
  fi

  if require_command dnf; then
    run_root dnf install -y ca-certificates curl rsync openssl
    return
  fi

  if require_command yum; then
    run_root yum install -y ca-certificates curl rsync openssl
    return
  fi

  echo "bootstrap-server.sh supports apt, dnf and yum based Linux distributions." >&2
  exit 1
}

install_prerequisites

install_docker_for_apt() {
  if ! require_command curl; then
    echo "curl must be available to install Docker automatically." >&2
    exit 1
  fi

  curl -fsSL https://get.docker.com | run_root sh
}

install_docker_for_dnf() {
  if ! run_root rpm -q dnf-plugins-core >/dev/null 2>&1; then
    run_root dnf install -y dnf-plugins-core
  fi

  run_root dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
  run_root dnf install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
}

install_docker_for_yum() {
  if ! require_command yum-config-manager; then
    run_root yum install -y yum-utils
  fi

  run_root yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
  run_root yum install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
}

if ! require_command docker; then
  if require_command apt-get; then
    install_docker_for_apt
  elif require_command dnf; then
    install_docker_for_dnf
  elif require_command yum; then
    install_docker_for_yum
  else
    echo "No supported package manager found for Docker installation." >&2
    exit 1
  fi
fi

if ! require_command systemctl; then
  echo "systemctl is required to manage Docker on the target server." >&2
  exit 1
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
