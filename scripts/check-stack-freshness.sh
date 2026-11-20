#!/usr/bin/env bash
# Freshness check for a stack profile: replaces per-product version research (MASTER_PROMPT §9.16.0, §9.21).
#   scripts/check-stack-freshness.sh <profile>
# Reports:
#   1. age of the last verification (VERIFIED.md)
#   2. support status of each runtime/framework line in toolkit/stacks/<profile>/freshness.conf (endoflife.date API)
#   3. newer releases of direct dependencies (the skeleton's scripts/check.sh outdated, run in Docker), except
#      packages deliberately held on a release line ("hold <package> <reason>" in freshness.conf, e.g. an LTS line)
# Exit 0 = still fresh; exit 1 = action needed (bump versions via an ADR, then scripts/verify-profile.sh <profile>).
set -uo pipefail
cd "$(dirname "$0")/.."
PROFILE="${1:?usage: $0 <profile>}"
SRC="toolkit/stacks/$PROFILE"
[ -f "$SRC/freshness.conf" ] || { echo "missing $SRC/freshness.conf"; exit 2; }
ACTION=0

verified="$(sed -n 's/^Verified: \([0-9-]*\).*/\1/p' "$SRC/VERIFIED.md" 2>/dev/null)"
status="$(sed -n 's/.*Status: \*\*\([A-Z]*\)\*\*.*/\1/p' "$SRC/VERIFIED.md" 2>/dev/null)"
if [ -z "$verified" ]; then echo "STALE verification: no VERIFIED.md"; ACTION=1
else
  age=$(( ( $(date -u +%s) - $(date -u -d "$verified" +%s) ) / 86400 ))
  if [ "$status" != PASS ] || [ "$age" -gt 30 ]; then echo "STALE verification: $verified ($age days, status $status)"; ACTION=1
  else echo "OK    verification: $verified ($age days, PASS)"; fi
fi

# freshness.conf lines: <endoflife.date product> <cycle> <pinned version>
while read -r product cycle pinned; do
  [[ -z "$product" || "$product" == \#* || "$product" == hold ]] && continue
  info="$(curl -s --max-time 20 "https://endoflife.date/api/$product/$cycle.json")"
  python3 - "$product" "$cycle" "$pinned" "$info" <<'PY' || ACTION=1
import json, sys, datetime
product, cycle, pinned, raw = sys.argv[1:5]
try:
    d = json.loads(raw)
except ValueError:
    print(f"WARN  {product} {cycle}: no data from endoflife.date"); sys.exit(0)
eol, latest = d.get("eol"), d.get("latest")
today = datetime.date.today().isoformat()
soon = (datetime.date.today() + datetime.timedelta(days=180)).isoformat()
if isinstance(eol, str) and eol <= today:
    print(f"EOL   {product} {cycle}: end of life {eol}; move to a supported line"); sys.exit(1)
note = f"supported until {eol}" if isinstance(eol, str) else "supported"
if isinstance(eol, str) and eol <= soon:
    note += " (ends within 6 months: plan the upgrade)"
def key(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.split("."))
if latest and pinned != "-" and key(latest) > key(pinned):
    print(f"PATCH {product} {cycle}: pinned {pinned}, latest {latest}; {note}"); sys.exit(1)
print(f"OK    {product} {cycle}: {pinned}; {note}")
PY
done < "$SRC/freshness.conf"

HOLDS="$(awk '$1=="hold"{print $2}' "$SRC/freshness.conf" | paste -sd'|' -)"
out="$("$SRC/skeleton/scripts/check.sh" outdated 2>&1)"
[ -n "$HOLDS" ] && out="$(grep -vE "(── |^)($HOLDS)(\[[^]]*\])? v" <<< "$out")"
echo "$out" | sed 's/^/      /'
[ -n "$HOLDS" ] && echo "      (held on purpose: ${HOLDS//|/, }; see freshness.conf)"
# uv prints "latest: x" per outdated package; npm outdated prints a "Package Current Wanted Latest" table.
grep -qE "latest:|Package +Current +Wanted" <<< "$out" && ACTION=1

if [ "$ACTION" = 0 ]; then echo "FRESH: profile $PROFILE can be used as is."
else echo "ACTION NEEDED: bump the flagged versions (ADR in the profile), then run scripts/verify-profile.sh $PROFILE."; fi
exit $ACTION
