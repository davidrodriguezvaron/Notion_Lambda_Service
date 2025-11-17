# Notion_Lambda_Service

## Local setup
- Clone the repo and use Python 3.12 (matches the Lambda runtime).
- Create a virtual environment:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- Copy the sample environment and fill in your values (at minimum `AWS_REGION`; add `AWS_PROFILE`, `FUNCTION_NAME`, `LAYER_NAME` if you need to override defaults):
  ```bash
  cp sample.env .env
  # edit .env
  ```
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Make helper scripts executable (run once after clone):
  ```bash
  chmod +x scripts/*.sh
  ```

## Running locally
- Unit tests: `scripts/run_tests.sh` (also runs inside `deploy_all.sh`).
- Invoke the Lambda handler locally with an optional event payload:
  ```bash
  scripts/invoke_local.sh            # uses {}
  scripts/invoke_local.sh scripts/event.json  # uses the provided JSON
  ```

## Deployment flow
- Full deploy (build layer, publish, attach, package, deploy code, cleanup) and tests:
  ```bash
  scripts/deploy_all.sh
  ```
- Ensure your AWS credentials/environment match what you set in `.env` (or exported vars) before running.

## Scripts reference
- `scripts/run_tests.sh` – run the unit test suite.
- `scripts/invoke_local.sh` – call `app.lambda_function.lambda_handler` locally.
- `scripts/build_layer.sh` – build the dependency layer (Docker, Amazon Linux image).
- `scripts/publish_layer.sh` – publish `layer.zip` as a Lambda layer.
- `scripts/attach_layer.sh` – attach the latest/passed layer ARN to the function.
- `scripts/package_code.sh` – zip the `app/` source as `lambda.zip`.
- `scripts/deploy_code.sh` – set the handler and upload `lambda.zip`.
- `scripts/cleanup_layers.sh` – prune old layer versions (keeps newest).
- `scripts/cleanup_function_versions.sh` – prune old function versions (keeps newest).
- `scripts/deploy_all.sh` – orchestrates tests → build/publish/attach → package → deploy → cleanup.

## Project structure
- `app/lambda_function.py` – Lambda entrypoint.
- `app/logic/` – application logic modules.
- `scripts/` – helper scripts for build, deploy, testing, local invocation.
- `tests/` – unit tests (`python -m unittest discover`).
