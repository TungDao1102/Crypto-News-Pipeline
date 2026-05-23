# Plan 06-02 — CI/CD Pipeline — Summary

## Objective
Create docker-compose.yml, .github/workflows/deploy.yml, and .ruff.toml for service orchestration and automation.

## Tasks Completed

### Task 1: .ruff.toml
- `target-version = "py314"`, `line-length = 120`
- `[lint] select = ["E", "F", "I", "N", "W"]`
- Excludes `__pycache__`
- Validated via `tomllib.load()` — parses correctly
- **Commit:** `311ba06`

### Task 2: docker-compose.yml
- Single service `pipeline` with `container_name: crypto-news-pipeline`
- `restart: unless-stopped`, `env_file: ./data/.env`
- 4 volume mounts: `.env:ro`, `sources.json:ro`, logs (rw), session (rw)
- Health check: `pgrep -f 'python -m src.main'`, interval 30s, timeout 5s, retries 3, start_period 15s
- No ports exposed (outbound-only daemon), no `build:` section (registry pull)
- Validated via YAML parse
- **Commit:** `4f3c722`

### Task 3: .github/workflows/deploy.yml
- Trigger: push to `main`, tags `v*`, `workflow_dispatch`
- Concurrency: `${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true`
- `ci` job: checkout@v4, setup-python@v5 (3.14), pip install (requirements + pytest/pytest-asyncio/ruff), `ruff check src/`, `python -m pytest -v`
- `cd` job (needs ci, if tag v*): checkout@v4, login to Docker Hub, setup-buildx, build-push-action@v7 (cache from/to gha), appleboy/ssh-action@v1 with `docker compose pull && up -d && docker system prune -f`
- 5 secrets referenced: DOCKERHUB_USERNAME, DOCKERHUB_TOKEN, SSH_HOST, SSH_USER, SSH_PRIVATE_KEY
- **Commit:** `60da80e`

## Verification
- `ruff.toml` — tomllib parsed, `target-version == 'py314'`, `E` in select
- `docker-compose.yml` — YAML parsed, restart: unless-stopped, healthcheck, 4 volumes, env_file
- `deploy.yml` — CI/CD job sections, build-push-action@v7, ssh-action@v1, concurrency, workflow_dispatch all present
- Test suite: 27/27 passed

## Key Decisions
- No `SSH_KNOWN_HOSTS` secret (optional, recommended — documented in DEPLOYMENT.md)
- Docker tags: both `latest` and version tag (`github.ref_name`)
- GHA cache for Docker layers (`type=gha,mode=max`)
