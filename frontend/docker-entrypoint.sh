#!/bin/sh
set -e

# TLS 인증서가 마운트돼 있으면 HTTPS 설정을, 없으면(로컬/개발) HTTP 설정을 사용한다.
CERT_DOMAIN="${CERT_DOMAIN:-h14k001.p.ssafy.io}"
CERT_FILE="/etc/letsencrypt/live/${CERT_DOMAIN}/fullchain.pem"

if [ -f "$CERT_FILE" ]; then
  echo "[entrypoint] TLS cert found for ${CERT_DOMAIN} -> HTTPS mode"
  cp /etc/nginx/available/https.conf /etc/nginx/conf.d/default.conf
else
  echo "[entrypoint] no TLS cert -> HTTP mode (local/dev)"
  cp /etc/nginx/available/http.conf /etc/nginx/conf.d/default.conf
fi

exec nginx -g 'daemon off;'
