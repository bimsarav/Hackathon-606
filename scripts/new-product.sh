#!/usr/bin/env bash
# Creates a product repository from a verified stack profile (toolkit/stacks/<profile>/).
#   scripts/new-product.sh <profile> <product-name> [destination]
# Default destination: products/<product-name>/source/<product-name>/ (PRODUCT_RULES §1).
# Copies the profile skeleton and its architecture document templates, then renames the sample identifiers:
#   sample-app -> <product-name>   sample_app -> <product_name>   Sample App -> <Product Name>
set -euo pipefail
cd "$(dirname "$0")/.."
PROFILE="${1:?usage: $0 <profile> <product-name> [destination]}"
NAME="${2:?usage: $0 <profile> <product-name> [destination]}"
SRC="toolkit/stacks/$PROFILE"
DEST="${3:-products/$NAME/source/$NAME}"

[[ "$NAME" =~ ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ ]] || { echo "product name must be kebab-case: $NAME"; exit 2; }
[ -d "$SRC/skeleton" ] || { echo "unknown profile: $PROFILE (see toolkit/stacks/README.md)"; exit 2; }
[ -e "$DEST" ] && { echo "destination already exists: $DEST"; exit 2; }

SNAKE="${NAME//-/_}"
TITLE="$(echo "$NAME" | tr '-' ' ' | awk '{for (i = 1; i <= NF; i++) $i = toupper(substr($i, 1, 1)) substr($i, 2)} 1')"

mkdir -p "$DEST"
# Copy without local build output (logs, virtualenvs, caches, node_modules, .env).
tar -C "$SRC/skeleton" \
  --exclude=logs --exclude=.venv --exclude=node_modules --exclude=dist --exclude=.env \
  --exclude=__pycache__ --exclude=.pytest_cache --exclude=.mypy_cache --exclude=.ruff_cache --exclude=.coverage \
  -cf - . | tar -C "$DEST" -xf -
mkdir -p "$DEST/docs"
tar -C "$SRC/docs" -cf - . | tar -C "$DEST/docs" -xf -

grep -rlI --exclude-dir=.git -e 'sample-app' -e 'sample_app' -e 'Sample App' "$DEST" | while IFS= read -r f; do
  sed -i -e "s/sample-app/$NAME/g" -e "s/sample_app/$SNAKE/g" -e "s/Sample App/$TITLE/g" "$f"
done
find "$DEST" -depth -name '*sample_app*' | while IFS= read -r p; do mv "$p" "${p//sample_app/$SNAKE}"; done

cat <<EOF
Created $DEST from profile $PROFILE ($(sed -n 's/^Verified: //p' "$SRC/VERIFIED.md" 2>/dev/null || echo "verification date unknown")).
Next:
  1. Fill the product-specific parts of $DEST/docs/architecture/*.md (marked TODO-PRODUCT).
  2. cd $DEST && scripts/check.sh        (quality gate: the compatibility proof for this product)
  3. cp .env.example .env && docker compose up --build
EOF
