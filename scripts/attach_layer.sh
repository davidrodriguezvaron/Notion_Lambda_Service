#!/usr/bin/env zsh
set -euo pipefail
export AWS_PAGER=""

# Attach a Layer to a Lambda function, preserving existing layers
# Config via env vars:
#   FUNCTION_NAME=Notion_Lambda_Service  (or pass as arg1)
#   AWS_PROFILE (optional)
#   AWS_REGION  (recommended)
# Usage:
#   scripts/attach_layer.sh <function_name> [layer_arn]

command -v aws >/dev/null 2>&1 || { echo "[attach-layer] AWS CLI is required" >&2; exit 1; }

FUNCTION_NAME=${1:-${FUNCTION_NAME:-}}
if [[ -z "$FUNCTION_NAME" ]]; then
  echo "[attach-layer] FUNCTION_NAME not provided" >&2
  echo "Usage: scripts/attach_layer.sh <function_name> [layer_arn]" >&2
  exit 1
fi

if [[ -n "${2:-}" ]]; then
  NEW_ARN="$2"
else
  if [[ -f last_layer_arn.txt ]]; then
    NEW_ARN=$(cat last_layer_arn.txt)
  else
    echo "[attach-layer] No layer ARN provided and last_layer_arn.txt not found" >&2
    exit 1
  fi
fi

PROFILE_ARGS=()
[[ -n "${AWS_PROFILE:-}" ]] && PROFILE_ARGS+=(--profile "$AWS_PROFILE")
REGION_ARGS=()
[[ -n "${AWS_REGION:-}" ]] && REGION_ARGS+=(--region "$AWS_REGION")

wait_for_function_ready() {
  local func_status
  echo "[attach-layer] Waiting for function to be ready..."
  for i in {1..45}; do
    func_status=$(aws lambda get-function-configuration \
      --function-name "$FUNCTION_NAME" \
      --no-cli-pager \
      ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
      ${REGION_ARGS:+${REGION_ARGS[@]}} \
      --query 'LastUpdateStatus' --output text)
    [[ "$func_status" == "Successful" ]] && return 0
    echo "[attach-layer] Waiting... ($i) Status: $func_status"
    sleep 2
  done
  echo "[attach-layer] ERROR: Function not ready after waits" >&2
  exit 1
}

echo "[attach-layer] Fetching existing layers for $FUNCTION_NAME"
EXISTING=$(aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query 'Layers[].Arn' \
  --output text \
  --no-cli-pager \
  ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
  ${REGION_ARGS:+${REGION_ARGS[@]}} || true)

# Build unique list including NEW_ARN, replacing any older version of the same layer
LAYERS_LIST=()
NEW_BASE=${NEW_ARN%:*}
if [[ -n "$EXISTING" ]]; then
  for arn in ${(z)EXISTING}; do
    BASE=${arn%:*}
    # Skip any existing version of the same layer base
    if [[ "$BASE" == "$NEW_BASE" ]]; then
      continue
    fi
    # Keep other layers (different bases)
    LAYERS_LIST+="$arn"
  done
fi
# Finally, add the new layer version
LAYERS_LIST+="$NEW_ARN"

echo "[attach-layer] Updating function layers"
wait_for_function_ready
for attempt in {1..5}; do
  if aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --layers ${LAYERS_LIST[@]} \
    --no-cli-pager \
    ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
    ${REGION_ARGS:+${REGION_ARGS[@]}} >/dev/null; then
    echo "[attach-layer] Done"
    exit 0
  fi
  echo "[attach-layer] Update in progress, retrying... ($attempt/5)"
  sleep 3
done

echo "[attach-layer] ERROR: Unable to update layers after retries" >&2
exit 1
