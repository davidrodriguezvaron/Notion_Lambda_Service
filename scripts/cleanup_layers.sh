#!/usr/bin/env zsh
set -euo pipefail

# Cleans up old Lambda Layer versions, keeping only the latest (RETAIN=1)
# Usage: scripts/cleanup_layers.sh [layer_name]

LAYER_NAME=${1:-${LAYER_NAME:-Notion_Lambda_Service_Deps}}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_PROFILE=${AWS_PROFILE:-lambda}
RETAIN=${RETAIN:-1}

PROFILE_ARGS=()
[[ -n "$AWS_PROFILE" ]] && PROFILE_ARGS+=(--profile "$AWS_PROFILE")
REGION_ARGS=()
[[ -n "$AWS_REGION" ]] && REGION_ARGS+=(--region "$AWS_REGION")

VERSIONS=($(aws lambda list-layer-versions \
  --layer-name "$LAYER_NAME" \
  --query 'reverse(sort_by(LayerVersions,&Version))[].Version' \
  --output text \
  --no-cli-pager \
  ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
  ${REGION_ARGS:+${REGION_ARGS[@]}}))

# zsh arrays are 1-based; keep the first RETAIN entries (newest), delete the rest
for ((i=RETAIN+1; i<=${#VERSIONS[@]}; i++)); do
  v=${VERSIONS[$i]}
  echo "[cleanup-layers] Deleting layer version $v..."
  aws lambda delete-layer-version \
    --layer-name "$LAYER_NAME" \
    --version-number "$v" \
    --no-cli-pager \
    ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
    ${REGION_ARGS:+${REGION_ARGS[@]}}
done
