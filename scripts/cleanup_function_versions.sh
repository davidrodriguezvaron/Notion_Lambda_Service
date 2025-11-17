#!/usr/bin/env zsh
set -euo pipefail

# Cleans up old Lambda function versions, keeping only the latest (RETAIN=1)
# Usage: scripts/cleanup_function_versions.sh [function_name]

command -v aws >/dev/null 2>&1 || { echo "[cleanup-function] AWS CLI is required" >&2; exit 1; }

FUNCTION_NAME=${1:-${FUNCTION_NAME:-Notion_Lambda_Service}}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_PROFILE=${AWS_PROFILE:-lambda}
RETAIN=${RETAIN:-1}

PROFILE_ARGS=()
[[ -n "$AWS_PROFILE" ]] && PROFILE_ARGS+=(--profile "$AWS_PROFILE")
REGION_ARGS=()
[[ -n "$AWS_REGION" ]] && REGION_ARGS+=(--region "$AWS_REGION")

ALL=($(aws lambda list-versions-by-function \
  --function-name "$FUNCTION_NAME" \
  --query 'reverse(sort_by(Versions[?Version!=`$LATEST`], &to_number(Version)))[].Version' \
  --output text \
  --no-cli-pager \
  ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
  ${REGION_ARGS:+${REGION_ARGS[@]}}))

# We already filtered $LATEST in the query; ALL is ordered newest->oldest
# zsh arrays are 1-based; keep the first RETAIN entries (newest), delete the rest
for ((i=RETAIN+1; i<=${#ALL[@]}; i++)); do
  v=${ALL[$i]}
  echo "[cleanup-function] Deleting function version $v..."
  aws lambda delete-function \
    --function-name "$FUNCTION_NAME" \
    --qualifier "$v" \
    --no-cli-pager \
    ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
    ${REGION_ARGS:+${REGION_ARGS[@]}}
done
