#!/usr/bin/env sh
# Render the Mermaid diagrams to PNG in the design-PDF theme (theme.json). Needs Docker.
# Usage: docs/architecture/diagrams/render.sh   (from the repository root)
set -eu
D="$(cd "$(dirname "$0")" && pwd)"
docker run --rm -u "$(id -u):$(id -g)" -v "$D:/data" --entrypoint sh minlag/mermaid-cli:11.12.0 -c \
  'for f in /data/mvp/*.mmd /data/current/*.mmd; do b=$(basename "$f" .mmd); /home/mermaidcli/node_modules/.bin/mmdc -p /puppeteer-config.json -i "$f" -o "/data/png/$b.png" -c /data/theme.json -b white -s 2 -w 1600 -q; done'
