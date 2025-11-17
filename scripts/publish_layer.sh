#!/usr/bin/env zsh
set -euo pipefail

# Publish the built layer.zip and print LayerVersionArn
# Config via env vars:
#   LAYER_NAME=Notion_Lambda_Service_Deps
#   RUNTIME=python3.12
#   AWS_PROFILE (optional)
#   AWS_REGION  (recommended)
# Usage:
#   scripts/publish_layer.sh [layer_name]

command -v aws >/dev/null 2>&1 || { echo "[publish-layer] AWS CLI is required" >&2; exit 1; }

LAYER_NAME=${1:-${LAYER_NAME:-Notion_Lambda_Service_Deps}}
RUNTIME=${RUNTIME:-python3.12}

if [[ ! -f layer.zip ]]; then
  echo "[publish-layer] layer.zip not found. Run scripts/build_layer.sh first." >&2
  exit 1
fi

PROFILE_ARGS=()
[[ -n "${AWS_PROFILE:-}" ]] && PROFILE_ARGS+=(--profile "$AWS_PROFILE")
REGION_ARGS=()
[[ -n "${AWS_REGION:-}" ]] && REGION_ARGS+=(--region "$AWS_REGION")

echo "[publish-layer] Publishing layer: $LAYER_NAME (runtime: $RUNTIME)"
ARN=$(aws lambda publish-layer-version \
  --layer-name "$LAYER_NAME" \
  --zip-file fileb://layer.zip \
  --compatible-runtimes "$RUNTIME" \
  --query 'LayerVersionArn' \
  --output text \
  ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
  ${REGION_ARGS:+${REGION_ARGS[@]}})

echo "$ARN" | tee last_layer_arn.txt
echo "[publish-layer] Done: $ARN"
