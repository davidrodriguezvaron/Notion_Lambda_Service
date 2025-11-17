#!/usr/bin/env zsh
set -euo pipefail

# Ensure handler is set and deploy lambda.zip code to AWS Lambda
# Config via env vars:
#   FUNCTION_NAME=Notion_Lambda_Service  (or pass as arg1)
#   HANDLER=app.lambda_function.lambda_handler
#   AWS_PROFILE (optional)
#   AWS_REGION  (recommended)
#   ZIP_NAME=lambda.zip
# Usage:
#   scripts/deploy_code.sh [function_name]

command -v aws >/dev/null 2>&1 || { echo "[deploy-code] AWS CLI is required" >&2; exit 1; }

FUNCTION_NAME=${1:-${FUNCTION_NAME:-}}
if [[ -z "$FUNCTION_NAME" ]]; then
  echo "[deploy-code] FUNCTION_NAME not provided" >&2
  echo "Usage: scripts/deploy_code.sh <function_name>" >&2
  exit 1
fi

HANDLER=${HANDLER:-app.lambda_function.lambda_handler}
ZIP_NAME=${ZIP_NAME:-lambda.zip}

if [[ ! -f "$ZIP_NAME" ]]; then
  echo "[deploy-code] $ZIP_NAME not found. Run scripts/package_code.sh first." >&2
  exit 1
fi

PROFILE_ARGS=()
[[ -n "${AWS_PROFILE:-}" ]] && PROFILE_ARGS+=(--profile "$AWS_PROFILE")
REGION_ARGS=()
[[ -n "${AWS_REGION:-}" ]] && REGION_ARGS+=(--region "$AWS_REGION")

wait_for_function_ready() {
  local label=${1:-}
  local func_status func_reason
  echo "[deploy-code] Waiting for function to be ready${label:+ ($label)}..."
  for i in {1..45}; do
    func_status=$(aws lambda get-function-configuration \
      --function-name "$FUNCTION_NAME" \
      --no-cli-pager \
      ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
      ${REGION_ARGS:+${REGION_ARGS[@]}} \
      --query 'LastUpdateStatus' --output text)
    if [[ "$func_status" == "Successful" ]]; then
      return 0
    elif [[ "$func_status" == "Failed" ]]; then
      func_reason=$(aws lambda get-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --no-cli-pager \
        ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
        ${REGION_ARGS:+${REGION_ARGS[@]}} \
        --query 'LastUpdateStatusReason' --output text)
      echo "[deploy-code] ERROR: Last update failed: $func_reason" >&2
      exit 1
    fi
    echo "[deploy-code] Waiting... ($i) Status: $func_status"
    sleep 2
  done
  echo "[deploy-code] ERROR: Function not ready after waiting" >&2
  exit 1
}

update_handler_with_retry() {
  local attempt=1 max_attempts=5 output
  while (( attempt <= max_attempts )); do
    if output=$(aws lambda update-function-configuration \
      --function-name "$FUNCTION_NAME" \
      --handler "$HANDLER" \
      --no-cli-pager \
      ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
      ${REGION_ARGS:+${REGION_ARGS[@]}} 2>&1 >/dev/null); then
      return 0
    fi

    if [[ "$output" == *"ResourceConflictException"* ]]; then
      echo "[deploy-code] Update in progress, retrying handler set... ($attempt/$max_attempts)"
      sleep 3
    else
      echo "[deploy-code] ERROR setting handler: $output" >&2
      exit 1
    fi
    (( attempt++ ))
  done
  echo "[deploy-code] ERROR: Unable to set handler after $max_attempts attempts" >&2
  exit 1
}

update_code_with_retry() {
  local attempt=1 max_attempts=5 output
  while (( attempt <= max_attempts )); do
    if output=$(aws lambda update-function-code \
      --function-name "$FUNCTION_NAME" \
      --zip-file fileb://"$ZIP_NAME" \
      --no-cli-pager \
      ${PROFILE_ARGS:+${PROFILE_ARGS[@]}} \
      ${REGION_ARGS:+${REGION_ARGS[@]}} 2>&1); then
      echo "$output"
      return 0
    fi

    if [[ "$output" == *"ResourceConflictException"* ]]; then
      echo "[deploy-code] Update in progress, retrying code upload... ($attempt/$max_attempts)"
      sleep 3
    else
      echo "[deploy-code] ERROR uploading code: $output" >&2
      exit 1
    fi
    (( attempt++ ))
  done
  echo "[deploy-code] ERROR: Unable to upload code after $max_attempts attempts" >&2
  exit 1
}

echo "[deploy-code] Setting handler: $HANDLER"
wait_for_function_ready "before handler update"
update_handler_with_retry

# Wait until the function is ready to avoid ResourceConflictException
echo "[deploy-code] Waiting for function to be ready before updating code..."
wait_for_function_ready "before code update"

echo "[deploy-code] Uploading code: $ZIP_NAME"
update_code_with_retry

echo "[deploy-code] Done"
