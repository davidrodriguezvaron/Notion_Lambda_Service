#!/usr/bin/env zsh
set -euo pipefail

# Invoke lambda_function.lambda_handler locally with an optional event JSON file
# Usage:
#   scripts/invoke_local.sh [event.json]

EVENT_FILE=${1:-}

if [[ -n "$EVENT_FILE" ]]; then
  if [[ ! -f "$EVENT_FILE" ]]; then
    echo "[invoke-local] Event file not found: $EVENT_FILE" >&2
    exit 1
  fi
  if [[ ! -s "$EVENT_FILE" ]]; then
    EVENT_PAYLOAD="{}"
  else
    EVENT_PAYLOAD=$(cat "$EVENT_FILE")
  fi
else
  EVENT_PAYLOAD="{}"
fi

echo "[invoke-local] Using event: $EVENT_PAYLOAD"

python - "$EVENT_PAYLOAD" <<'PY'
import json
import sys
from app.lambda_function import lambda_handler

payload = sys.argv[1] if len(sys.argv) > 1 else "{}"
event = json.loads(payload or "{}")
result = lambda_handler(event, None)
print(json.dumps(result, indent=2, ensure_ascii=False))
PY
