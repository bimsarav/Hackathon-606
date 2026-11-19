#!/usr/bin/env bash
# Generates an RS256 key pair for directory-service and prints .env lines (single-line PEM with \n escapes).
#   scripts/gen-jwt-keys.sh >> .env
set -euo pipefail
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$tmp/private.pem" 2>/dev/null
openssl pkey -in "$tmp/private.pem" -pubout -out "$tmp/public.pem"
oneline() { awk 'BEGIN{ORS="\\n"} {print}' "$1"; }
echo "ESM_JWT_PRIVATE_KEY=\"$(oneline "$tmp/private.pem")\""
echo "ESM_JWT_PUBLIC_KEY=\"$(oneline "$tmp/public.pem")\""
