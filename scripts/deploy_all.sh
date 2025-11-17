#!/usr/bin/env zsh
set -euo pipefail

# Orchestrates the full flow: build layer -> publish -> attach -> package -> deploy
# Loads variables from .env if present and allows environment overrides
#
# Variables used (can come from environment or .env):
#   AWS_PROFILE       (optional)
#   AWS_REGION        (required)
#   FUNCTION_NAME     (default: Notion_Lambda_Service)
#   LAYER_NAME        (default: Notion_Lambda_Service_Deps)
#   RUNTIME           (default: python3.12)
#   LAMBDA_ARCH       (default: x86_64)  # or arm64
#   REQ_FILE          (default: requirements.txt)
#
#
# Usage:
#   scripts/deploy_all.sh

# 1) Load .env if present (auto-exports variables defined there)
if [[ -f .env ]]; then
  echo "[deploy-all] Loading .env"
  set -a
  source .env
  set +a
fi

# 2) Reasonable defaults
: ${FUNCTION_NAME:=Notion_Lambda_Service}
: ${LAYER_NAME:=Notion_Lambda_Service_Deps}
: ${RUNTIME:=python3.12}
: ${LAMBDA_ARCH:=x86_64}
: ${REQ_FILE:=requirements.txt}

# 3) Basic validations
if [[ -z "${AWS_REGION:-}" ]]; then
  echo "[deploy-all] ERROR: AWS_REGION is not defined. Export it or add it to .env" >&2
  exit 1
fi

echo "[deploy-all] Context"
echo "  FUNCTION_NAME = $FUNCTION_NAME"
echo "  LAYER_NAME    = $LAYER_NAME"
echo "  RUNTIME       = $RUNTIME"
echo "  LAMBDA_ARCH   = $LAMBDA_ARCH"
echo "  AWS_REGION    = ${AWS_REGION}"
echo "  AWS_PROFILE   = ${AWS_PROFILE:-default}"
echo "  REQ_FILE      = $REQ_FILE"

echo "[deploy-all] Running tests..."
scripts/run_tests.sh

scripts/build_layer.sh "$REQ_FILE"

scripts/publish_layer.sh "$LAYER_NAME"

scripts/attach_layer.sh "$FUNCTION_NAME"

scripts/package_code.sh

scripts/deploy_code.sh "$FUNCTION_NAME"


# Cleanup old layer and function versions (keep only latest)
echo "[deploy-all] Cleaning old layer and function versions..."
scripts/cleanup_layers.sh "$LAYER_NAME" || echo "[deploy-all] WARNING: cleanup_layers.sh failed"
scripts/cleanup_function_versions.sh "$FUNCTION_NAME" || echo "[deploy-all] WARNING: cleanup_function_versions.sh failed"

echo "[deploy-all] DONE"
