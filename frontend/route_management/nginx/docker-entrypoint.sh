#!/bin/sh
set -eu

: "${VITE_API_URL:=/api/}"
: "${VITE_WS_BASE_URL:=}"
: "${VITE_DIRECT_MEDIA_UPLOAD:=True}"
: "${BACKEND_UPSTREAM:=http://route-management-backend:8000}"
: "${AI_UPSTREAM:=http://route-management-ai-service:8001}"

envsubst '${VITE_API_URL} ${VITE_WS_BASE_URL} ${VITE_DIRECT_MEDIA_UPLOAD}' \
  < /etc/nginx/templates/runtime-config.template.js \
  > /usr/share/nginx/html/runtime-config.js

envsubst '${BACKEND_UPSTREAM} ${AI_UPSTREAM}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
