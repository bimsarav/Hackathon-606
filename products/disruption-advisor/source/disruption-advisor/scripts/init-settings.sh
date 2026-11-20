#!/usr/bin/env bash
# Creates the visible settings file and the link Docker Compose needs.
#   settings.env  the real settings (secrets): visible, mode 600, git-ignored
#   .env          a link to settings.env, because Docker Compose only reads a file named .env
# Safe to re-run: an existing settings.env is never overwritten; an existing plain .env is moved into settings.env.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -e settings.env ]; then
  if [ -f .env ] && [ ! -L .env ]; then mv .env settings.env; echo "moved existing .env to settings.env"
  else cp settings.env.example settings.env; echo "created settings.env from settings.env.example: fill it in"; fi
fi
chmod 600 settings.env
[ -L .env ] || { [ -e .env ] && { echo "a .env file exists and is not a link; resolve it first" >&2; exit 1; }; ln -s settings.env .env; }
echo "ok: settings.env (mode $(stat -c %a settings.env)), .env -> $(readlink .env)"
