#!/usr/bin/env bash
# Re-verifies a stack profile end to end and records the result in toolkit/stacks/<profile>/VERIFIED.md.
#   scripts/verify-profile.sh <profile>
# Steps (all in Docker; output in <work>/logs, console shows one line per step):
#   1. generate a product copy with scripts/new-product.sh (tests the generator and the renaming too)
#   2. quality gate: <copy>/scripts/check.sh (lint, types, unit + integration tests)
#   3. deployment smoke test: <copy>/scripts/smoke.sh (compose build + up + endpoint checks + down)
#   4. Trivy: dependency/secret/misconfiguration scan of the skeleton, and HIGH/CRITICAL fixable scan of each image
set -euo pipefail
cd "$(dirname "$0")/.."
PROFILE="${1:?usage: $0 <profile>}"
SRC="toolkit/stacks/$PROFILE"
[ -d "$SRC/skeleton" ] || { echo "unknown profile: $PROFILE"; exit 2; }
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.76.2}"
NAME="verify-${PROFILE//_/-}"
WORK="${VERIFY_WORKDIR:-${TMPDIR:-/tmp}/stack-verify}/$NAME-$(date -u +%Y%m%d%H%M%S)"
mkdir -p "$(dirname "$WORK")"
RESULTS=()
step() { RESULTS+=("| $1 | $2 |"); echo "$2 $1"; }

scripts/new-product.sh "$PROFILE" "$NAME" "$WORK" > /dev/null && step "generate product copy (scripts/new-product.sh)" PASS
if (cd "$WORK" && scripts/check.sh > "$WORK/verify-check.txt" 2>&1); then
  step "quality gate (scripts/check.sh): $(grep -E 'passed|Tests ' "$WORK/verify-check.txt" | tr -s ' ' | paste -sd ';' -)" PASS
else step "quality gate (scripts/check.sh), see $WORK/verify-check.txt" FAIL; fi
if (cd "$WORK" && scripts/smoke.sh > "$WORK/verify-smoke.txt" 2>&1); then
  step "deployment smoke test (scripts/smoke.sh): $(grep -c '^PASS' "$WORK/verify-smoke.txt") checks" PASS
else step "deployment smoke test (scripts/smoke.sh), see $WORK/verify-smoke.txt" FAIL; fi

docker volume create trivy-cache > /dev/null
trivy() { docker run --rm -v trivy-cache:/root/.cache -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$SRC/skeleton":/src:ro "$TRIVY_IMAGE" "$@"; }
count() { python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(len(r.get(k) or []) for r in d.get('Results', []) for k in ('Vulnerabilities', 'Secrets', 'Misconfigurations')))"; }
n="$(trivy fs --quiet --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --ignore-unfixed --skip-dirs node_modules --format json /src | count)"
[ "$n" = 0 ] && step "Trivy fs: dependencies, secrets, Dockerfile/compose misconfiguration (HIGH/CRITICAL)" PASS \
             || step "Trivy fs: $n HIGH/CRITICAL findings" FAIL
for image in $(cd "$WORK" && docker compose config --images | sort -u | grep "^$NAME"); do
  n="$(trivy image --quiet --severity HIGH,CRITICAL --ignore-unfixed --format json "$image" | count)"
  [ "$n" = 0 ] && step "Trivy image $image: 0 fixable HIGH/CRITICAL" PASS || step "Trivy image $image: $n fixable HIGH/CRITICAL" FAIL
done

STATUS=PASS; for r in "${RESULTS[@]}"; do [[ "$r" == *"| FAIL |" ]] && STATUS=FAIL; done
{
  echo "# $PROFILE: verification record"
  echo
  echo "Verified: $(date -u +%Y-%m-%d) · Status: **$STATUS** · Host: Docker $(docker version --format '{{.Server.Version}}'), Compose $(docker compose version --short)"
  echo
  echo "Produced by \`scripts/verify-profile.sh $PROFILE\`. Do not edit by hand; re-run the script instead."
  echo "A profile whose last PASS is older than 30 days needs \`scripts/check-stack-freshness.sh $PROFILE\` before use (MASTER_PROMPT §9.16.0)."
  echo
  echo "| Step | Result |"
  echo "|---|---|"
  printf '%s\n' "${RESULTS[@]}"
} > "$SRC/VERIFIED.md"
echo "$STATUS: wrote $SRC/VERIFIED.md (work copy: $WORK)"
[ "$STATUS" = PASS ]
