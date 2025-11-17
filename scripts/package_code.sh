#!/usr/bin/env zsh
set -euo pipefail

# Package only the source code (app/) into lambda.zip
# Ensures app/ is at zip root and excludes caches/tests
# Usage:
#   scripts/package_code.sh

ZIP_NAME=${ZIP_NAME:-lambda.zip}
SRC_DIR=app

if [[ ! -d "$SRC_DIR" ]]; then
  echo "[package-code] $SRC_DIR directory not found" >&2
  exit 1
fi

rm -f "$ZIP_NAME"

echo "[package-code] Creating $ZIP_NAME from $SRC_DIR"
zip -r "$ZIP_NAME" "$SRC_DIR" \
  -x "*.DS_Store" \
     "${SRC_DIR}/**/__pycache__/*" \
     "${SRC_DIR}/**/*.pyc" \
     "${SRC_DIR}/**/tests/*" \
     "tests/*" \
     "layer/*" \
     "$ZIP_NAME" >/dev/null

echo "[package-code] Done: $ZIP_NAME"
