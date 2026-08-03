#!/bin/sh
set -eu

DEPLOY_ROOT="${1:-/opt/portfolio}"
SERVICE_PATH="/etc/systemd/system/portfolio-cert-renew.service"
TIMER_PATH="/etc/systemd/system/portfolio-cert-renew.timer"
RENEW_SCRIPT="${DEPLOY_ROOT}/app/current/scripts/deploy/renew-certificates.sh"

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

cat <<EOF | run_root tee "${SERVICE_PATH}" >/dev/null
[Unit]
Description=Renew Let's Encrypt certificates for the portfolio stack
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=${RENEW_SCRIPT} ${DEPLOY_ROOT}
EOF

cat <<EOF | run_root tee "${TIMER_PATH}" >/dev/null
[Unit]
Description=Twice-daily Let's Encrypt renewal timer for the portfolio stack

[Timer]
OnCalendar=*-*-* 03,15:00:00
RandomizedDelaySec=15m
Persistent=true

[Install]
WantedBy=timers.target
EOF

run_root systemctl daemon-reload
run_root systemctl enable --now portfolio-cert-renew.timer
