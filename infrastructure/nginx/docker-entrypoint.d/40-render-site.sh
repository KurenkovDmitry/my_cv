#!/bin/sh
set -eu

: "${DOMAIN_NAME:?DOMAIN_NAME is required}"

export DOMAIN_NAME
export ADMIN_BASE_PATH="${ADMIN_BASE_PATH:-/admin}"
export API_UPSTREAM="${API_UPSTREAM:-http://api:8000}"

if [ "${ADMIN_BASE_PATH}" != "/" ]; then
  ADMIN_BASE_PATH="${ADMIN_BASE_PATH%/}"
fi

export ADMIN_BASE_PATH

template_path="/etc/nginx/templates/site.http.conf.template"

if [ "${ENABLE_HTTPS:-true}" = "true" ] \
  && [ -f "/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem" ] \
  && [ -f "/etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem" ]; then
  template_path="/etc/nginx/templates/site.https.conf.template"
fi

envsubst '${DOMAIN_NAME} ${ADMIN_BASE_PATH} ${API_UPSTREAM}' \
  < "${template_path}" \
  > /etc/nginx/conf.d/default.conf
