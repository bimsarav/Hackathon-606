#!/usr/bin/env bash
# Archives the logs and tracking files of a finished (or dropped) product run, then resets them so the
# next product starts with empty logs. See instructions/CHECKPOINT_PROTOCOL.md §10.
#
#   scripts/archive-product-logs.sh <product-name> [--status delivered|dropped] [--yes]
#
# Moves (never deletes):
#   execution/logs/*            → execution/archive/<product>-<UTC stamp>/logs/
#   execution/*.md (tracking)   → execution/archive/<product>-<UTC stamp>/tracking/
# Then writes empty logs and fresh tracking files from execution/templates/.
# execution/archive/ is git-ignored (archives are local only); the fresh, unfinished-run logs are committed.
set -euo pipefail
cd "$(dirname "$0")/.."

NAME="${1:-}"; shift || true
STATUS="delivered"; YES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --status) STATUS="${2:?}"; shift 2 ;;
    --yes) YES=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ "$NAME" =~ ^[a-z0-9][a-z0-9-]{1,60}$ ]] || { echo "usage: $0 <product-name (kebab-case)> [--status delivered|dropped] [--yes]" >&2; exit 2; }
[[ "$STATUS" =~ ^(delivered|dropped)$ ]] || { echo "--status must be delivered or dropped" >&2; exit 2; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="execution/archive/${NAME}-${STAMP}"
[ -e "$DEST" ] && { echo "archive already exists: $DEST" >&2; exit 1; }
TRACKING=(PROJECT_STATUS CURRENT_TASK NEXT_ACTION TASK_BACKLOG DECISIONS ASSUMPTIONS BLOCKERS CHANGELOG RESUME DEPLOYMENT_STATUS)

if [ -z "$YES" ]; then
  read -r -p "Archive the current run as '$NAME' ($STATUS) and reset logs + tracking files? [y/N] " a
  [ "$a" = "y" ] || { echo "aborted"; exit 1; }
fi

mkdir -p "$DEST/logs" "$DEST/tracking"
# 1. Move the logs (including rotated activity logs and saved command output)
shopt -s nullglob dotglob
for f in execution/logs/*; do
  [ "$(basename "$f")" = ".gitkeep" ] && continue
  mv "$f" "$DEST/logs/"
done
# 2. Move the tracking snapshot
for t in "${TRACKING[@]}"; do
  [ -f "execution/$t.md" ] && mv "execution/$t.md" "$DEST/tracking/"
done
# 3. Manifest with checksums, so the archive can be verified later
{
  echo "# Archive: $NAME"
  echo "- Status: $STATUS"
  echo "- Archived (UTC): $STAMP"
  echo "- Git commit at archive time: $(git rev-parse --short HEAD 2>/dev/null || echo n/a)"
  if [ -d "products/$NAME" ]; then echo "- Product folder: products/$NAME/"; else echo "- Product folder: none (not created)"; fi
  echo
  echo '```'
  (cd "$DEST" && find logs tracking -type f -print0 | sort -z | xargs -0 sha256sum)
  echo '```'
} > "$DEST/ARCHIVE.md"

# 4. Start the next run: empty logs and fresh tracking files
mkdir -p execution/logs/output
DATE_UTC="$(date -u +%Y-%m-%dT%H:%MZ)"
for l in execution decisions errors; do
  echo "# ${l}.log: new product run started $DATE_UTC (previous run: $DEST)" > "execution/logs/${l}.log"
done
: > execution/logs/sessions.log
: > execution/logs/tool-activity.log
touch execution/logs/output/.gitkeep
for t in "${TRACKING[@]}"; do
  sed -e "s|{{DATE}}|$DATE_UTC|g" -e "s|{{ARCHIVE}}|$DEST|g" "execution/templates/$t.md" > "execution/$t.md"
done

echo "archived to $DEST ($(du -sh "$DEST" | cut -f1)); logs and tracking files reset"
