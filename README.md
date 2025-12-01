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
- Install production dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Install development dependencies (for testing and linting):
  ```bash
  pip install -r requirements-dev.txt
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

## Code Quality

- Run linting and formatting:
  ```bash
  scripts/lint.sh
  ```
  This runs:
  - **Black**: Auto-formats code to PEP 8 standards
  - **Flake8**: Checks for style violations and errors
- Configuration:
  - `.flake8` – Flake8 rules (max line length, excluded directories, etc.)

## Deployment flow

- Full deploy (build layer, publish, attach, package, deploy code, cleanup) and tests:
  ```bash
  scripts/deploy_all.sh
  ```
- Ensure your AWS credentials/environment match what you set in `.env` (or exported vars) before running.

## Scripts reference

- `scripts/run_tests.sh` – run the unit test suite with coverage (fails if < 75%).
- `scripts/lint.sh` – run code formatting (black) and linting (flake8).
- `scripts/invoke_local.sh` – call `app.lambda_function.lambda_handler` locally.
- `scripts/build_layer.sh` – build the dependency layer (Docker, Amazon Linux image).
- `scripts/publish_layer.sh` – publish `layer.zip` as a Lambda layer.
- `scripts/attach_layer.sh` – attach the latest/passed layer ARN to the function.
- `scripts/package_code.sh` – zip the `app/` source as `lambda.zip`.
- `scripts/deploy_code.sh` – set the handler and upload `lambda.zip`.
- `scripts/cleanup_layers.sh` – prune old layer versions (keeps newest).
- `scripts/cleanup_function_versions.sh` – prune old function versions (keeps newest).
- `scripts/deploy_all.sh` – orchestrates tests → build/publish/attach → package → deploy → cleanup.

## CI/CD Pipeline

The project uses GitHub Actions for Continuous Integration and Deployment.

### Workflows

1.  **CI Develop (`.github/workflows/ci-develop.yml`)**:

    - Triggers on push to `develop`.
    - Runs linting (Black, Flake8) and tests (Pytest with coverage).
    - Automatically creates a Pull Request to `main` if successful.

2.  **PR Main (`.github/workflows/pr-main.yml`)**:

    - Triggers on Pull Request to `main`.
    - Runs SonarQube analysis (Quality Gate).
    - **Auto-Merge**: Automatically merges the PR (Squash) if checks pass.

3.  **Deploy Main (`.github/workflows/deploy-main.yml`)**:
    - Triggers on Push to `main` (after merge).
    - Deploys to AWS using `scripts/deploy_all.sh` (skips tests).

### Configuration

To enable the pipeline, configure the following **Repository Secrets** in GitHub:

- `AWS_ACCESS_KEY_ID`: AWS Access Key for deployment.
- `AWS_SECRET_ACCESS_KEY`: AWS Secret Key for deployment.
- `SONAR_TOKEN`: Token for SonarCloud analysis.

The `GITHUB_TOKEN` is automatically handled by GitHub Actions.

## Project structure

- `app/lambda_function.py` – Lambda entrypoint.
- `app/common/` – shared utilities (logging, environment handling).
- `app/logic/` – application logic modules.
- `scripts/` – helper scripts for build, deploy, testing, local invocation.
- `tests/` – unit tests (pytest).
- `requirements.txt` – production dependencies.
- `requirements-dev.txt` – development dependencies (pytest, black, flake8).

## Notion Integration

The project includes a generic `NotionClient` to interact with the Notion API.

### Configuration

Ensure the following environment variables are set:

- `NOTION_API_KEY`: Your Notion integration token.
- `NOTION_VERSION`: (Optional) The Notion API version (default: "2022-06-28").
- `LOG_LEVEL`: (Optional) Logging level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO in Production, DEBUG in Local.

### Usage

```python
from app.common.integrations.notion import NotionClient

# Initialize the client
notion = NotionClient()

# Example: Get a database
# database_id = "your-database-id"
# response = notion.get(f"databases/{database_id}")

# Example: Query a database
# response = notion.post(f"databases/{database_id}/query", {"filter": {...}})
```
