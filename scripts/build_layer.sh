#!/usr/bin/env zsh
set -euo pipefail

# Build an AWS Lambda Layer from requirements.txt using Docker (Amazon Linux compatible)
# - Uses AWS SAM builder image to avoid Lambda runtime entrypoint issues
# - Produces: layer/python (on disk) and layer.zip (zip with python/ at root)
#
# Config via env vars (override as needed):
#   RUNTIME=python3.12         # Python runtime
#   LAMBDA_ARCH=x86_64         # or arm64
#   AWS_PROFILE=lambda         # optional
#
# Usage:
#   scripts/build_layer.sh [requirements_file]

RUNTIME=${RUNTIME:-python3.12}
LAMBDA_ARCH=${LAMBDA_ARCH:-x86_64}
REQ_FILE=${1:-requirements.txt}
LAYER_DIR="layer"
SITE_DIR="${LAYER_DIR}/python"

# Map Lambda arch to Docker platform
case "$LAMBDA_ARCH" in
  x86_64) DOCKER_PLATFORM=linux/amd64 ;;
  arm64)  DOCKER_PLATFORM=linux/arm64 ;;
  *) echo "[build-layer] Unknown LAMBDA_ARCH: $LAMBDA_ARCH (use x86_64 or arm64)" >&2; exit 1 ;;
esac

IMAGE="public.ecr.aws/sam/build-${RUNTIME}"

echo "[build-layer] Runtime: $RUNTIME | Arch: $LAMBDA_ARCH | Image: $IMAGE"
echo "[build-layer] Requirements: $REQ_FILE"

command -v docker >/dev/null 2>&1 || { echo "[build-layer] Docker is required" >&2; exit 1; }

rm -rf "$LAYER_DIR" layer.zip
mkdir -p "$SITE_DIR"

if [[ ! -f "$REQ_FILE" ]] || [[ ! -s "$REQ_FILE" ]]; then
  echo "[build-layer] WARNING: $REQ_FILE missing or empty. Building an empty layer."
else
  echo "[build-layer] Installing dependencies into $SITE_DIR using $IMAGE"
  docker run --rm \
    --platform "$DOCKER_PLATFORM" \
    -v "$PWD":/var/task -w /var/task \
    "$IMAGE" \
    bash -lc "python -m pip install --upgrade pip --root-user-action=ignore && pip install --root-user-action=ignore -r '$REQ_FILE' -t '$SITE_DIR'"
fi

echo "[build-layer] Creating layer.zip"
(
  cd "$LAYER_DIR"
  zip -r ../layer.zip python -x "*.DS_Store" "*__pycache__*" "*.pyc" >/dev/null
)

echo "[build-layer] Done: layer.zip created"
