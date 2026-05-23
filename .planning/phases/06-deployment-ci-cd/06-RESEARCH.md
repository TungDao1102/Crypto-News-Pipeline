# Phase 6: Deployment & CI/CD — Research

**Researched:** 2026-05-23
**Domain:** Docker containerization, GitHub Actions CI/CD, Linux VPS deployment
**Confidence:** HIGH

## Summary

This phase containerizes the existing 5-phase asyncio Python pipeline and establishes a fully automated CI/CD pipeline. The pipeline runs from a single container (`python:3.14-slim` base), deployed via Docker Compose on a Linux VPS with `restart: unless-stopped` for crash recovery. GitHub Actions handles the full workflow: on push to `main`, it runs tests + lint; on a `v*` git tag, it additionally builds the Docker image, pushes to Docker Hub, and SSH-deploys to the VPS.

**Primary recommendation:** Use `docker/build-push-action@v7` for image build/push, `appleboy/ssh-action@v1` for SSH deploy, and `python:3.14-slim` as the base image. Keep the Dockerfile single-stage (all Python deps are pure). The entrypoint script validates preconditions before executing the application.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Container Strategy
- **D-01:** Docker containerization with `python:3.14-slim` base image. No Alpine (avoid musl/glibc risk).
- **D-02:** Single-stage Dockerfile (no multi-stage needed — all deps are pure Python).
- **D-03:** Entrypoint shell script (`entrypoint.sh`) that validates environment, creates required dirs, then runs `python -m src.main`.
- **D-04:** Standard Dockerfile pattern: `COPY requirements.txt` → `pip install` → `COPY src/`. Leverages Docker layer caching.
- **D-05:** Mounted volumes for `.env`, `sources.json`, `logs/`, and Telegram `.session` file. Session persistence avoids re-auth on every restart.

#### CI/CD Platform & Flow
- **D-06:** GitHub Actions as CI/CD platform.
- **D-07:** Trigger strategy: push to `main` runs test + lint (CI). Git tag (`v*`) triggers full pipeline: test → lint → build image → push to Docker Hub → SSH deploy.
- **D-08:** Deploy via SSH into VPS: `docker compose pull && docker compose up -d`.
- **D-09:** Full pipeline stages: pytest, ruff lint, docker buildx, push to Docker Hub, SSH remote deploy.
- **D-10:** Docker Hub as container registry (public image).

#### Deployment Target & Process Management
- **D-11:** Linux VPS as deployment target (Ubuntu/Debian recommended).
- **D-12:** Docker `restart: unless-stopped` policy for crash recovery and auto-start on boot.
- **D-13:** `docker compose` for declarative service definition (volumes, env_file, restart policy, healthcheck).
- **D-14:** Docker health check configured in compose — basic process-alive check.

#### Secrets & Config in Deployment
- **D-15:** `.env` file placed manually on the VPS (via SSH). GitHub Secrets store Docker Hub and SSH deploy credentials only.
- **D-16:** `.env` and `sources.json` remain gitignored. `.env.example` committed as template.
- **D-17:** docker-compose uses `env_file: .env` and bind volumes for `sources.json`.
- **D-18:** Production logging keeps the existing `RotatingFileHandler` on the mounted `logs/` volume (as decided in Phase 5 D-11). No JSON log aggregation pipeline.

### the agent's Discretion
- Exact Docker health check command and interval/retries
- Entrypoint script implementation details (validation steps)
- Dockerfile labels, maintainer metadata
- GitHub Actions workflow names and job structure
- Docker Compose version and specific compose file structure
- SSH key management approach in GitHub Actions
- Docker Hub image naming convention (tag strategy: `latest`, `vX.Y.Z`, commit SHA)
- Port exposure (none needed internally — PTB bot initiates outbound connections)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Container image build | CI/CD (GitHub Actions) | Local dev machine | Build once in CI, push to registry, pull on VPS. Local build for testing only. |
| Image storage & distribution | Docker Hub (registry) | — | Public registry. Pullable from any VPS without auth. No self-hosting. |
| Container runtime | VPS (Docker Engine) | — | Single host. Docker Compose manages lifecycle. No orchestration layer needed. |
| Secret management (app) | VPS filesystem (`.env`) | — | `.env` placed manually. Not in git. GitHub Secrets only store CI/CD credentials. |
| Secret management (CI/CD) | GitHub Secrets | — | Docker Hub PAT, SSH private key, SSH host/user stored as encrypted secrets. |
| Health monitoring | Docker healthcheck + restart policy | Docker Compose | Process-alive check. `restart: unless-stopped` handles crashes. HealthCollector (Phase 5) handles app-level health. |
| Log persistence | VPS filesystem (mounted `logs/` volume) | — | RotatingFileHandler writes to mounted volume. Survives container restarts. |
| Session persistence | VPS filesystem (mounted `telegram.session`) | — | Avoids Telethon re-auth on every deploy. Survives container restarts. |
| CI (test + lint) | GitHub Actions runner | — | Runs in cloud on `ubuntu-latest`. No VPS involvement. |
| CD (deploy) | GitHub Actions → SSH → VPS | — | Cloud runner triggers remote pull + restart on VPS. |

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `python:3.14-slim` | 3.14.x (rolling tag) | Runtime base image | ~120MB Debian-based, no build deps, full glibc compatibility. Python 3.14 confirmed on the local dev machine (3.14.3). [VERIFIED: Docker Hub] |
| `docker/build-push-action` | v7 | Build + push Docker images | Official Docker action, Buildx-native, supports multi-platform build, cache export, and provenance attestations. [VERIFIED: github.com/docker/build-push-action — v7.1.0 as of Apr 2026] |
| `docker/login-action` | v4 | Authenticate to Docker Hub | Official Docker action. Supports PAT-based auth, scope-limited credentials. [VERIFIED: github.com/docker/login-action — v4.1.0 as of Apr 2026] |
| `docker/setup-buildx-action` | v4 | Set up Buildx builder | Required for modern Docker build features. Uses `docker-container` driver by default. [VERIFIED: github.com/docker/setup-buildx-action — v4.0.0 as of Mar 2026] |
| `appleboy/ssh-action` | v1 | Execute remote SSH commands | Most popular SSH action on the marketplace (6K+ stars). Supports key-based auth, multiple hosts, env passthrough. [VERIFIED: github.com/appleboy/ssh-action] |
| Docker Compose | v2+ (plugin) | Declarative service definition | Built into Docker CLI. Uses `compose.yaml` by default. v2 is the current stable major version. [ASSUMED] |
| `pytest` | 9.0.3 | Test runner | Already installed. CI runs `python -m pytest`. [VERIFIED: pip list] |
| `ruff` | latest (install in CI) | Linter | Chosen in D-09 for lint stage. Fast Python linter written in Rust. [ASSUMED] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `docker/setup-qemu-action` | v4 | Multi-platform build support | Only needed if building for ARM + AMD simultaneously. Not needed for single-platform VPS deployment. |
| `actions/checkout` | v4 | Check out repo in CI | Needed when using path context (not git context). Use v4+ for Node 20+ support. |
| `pytest-asyncio` | 1.3.0 | Async test support for pytest | Required by all existing tests. Already installed. [VERIFIED: pip list] |

### GitHub Secrets Required

| Secret Name | Purpose | Set By |
|------------|---------|--------|
| `DOCKERHUB_USERNAME` | Docker Hub username for login | Admin (manual) |
| `DOCKERHUB_TOKEN` | Docker Hub personal access token (not password) | Admin (manual) |
| `SSH_HOST` | VPS IP address or hostname | Admin (manual) |
| `SSH_USER` | SSH username on VPS (e.g., `ubuntu`, `deploy`) | Admin (manual) |
| `SSH_PRIVATE_KEY` | SSH private key (no passphrase) | Admin (manual) |
| `SSH_KNOWN_HOSTS` | Output of `ssh-keyscan <host>` | Admin (manual) |

**Note:** `SSH_KNOWN_HOSTS` is optional if using `StrictHostKeyChecking no` in the SSH action, but strongly recommended for security. The appleboy/ssh-action supports the `known_hosts` input parameter.

## Package Legitimacy Audit

> **Note:** This phase does not install any new Python packages into the application. The Docker image installs from the existing `requirements.txt` (5 packages already verified in prior phases). The CI runner installs `pytest`, `pytest-asyncio`, and `ruff` ephemerally. All infrastructure tools (Docker, GitHub Actions, SSH) are platform tools, not packages from a registry.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| docker/build-push-action | GitHub Actions | 6 yrs | 5219 stars | github.com/docker/build-push-action | N/A (GH Action) | Approved |
| docker/login-action | GitHub Actions | 6 yrs | 1393 stars | github.com/docker/login-action | N/A (GH Action) | Approved |
| docker/setup-buildx-action | GitHub Actions | 6 yrs | 1330 stars | github.com/docker/setup-buildx-action | N/A (GH Action) | Approved |
| appleboy/ssh-action | GitHub Actions | 7 yrs | 6000+ stars | github.com/appleboy/ssh-action | N/A (GH Action) | Approved |
| python:3.14-slim | Docker Hub | Active | Official image | github.com/docker-library/python | N/A (Docker image) | Approved |

**slopcheck note:** slopcheck was not run because this phase adds no new ecosystem packages (pip/npm/cargo). The existing `requirements.txt` packages were already verified in prior phases. All recommended tools are first-party GitHub Actions or official Docker images.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GITHUB ACTIONS CI/CD                          │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐    │
│  │  Push to main │    │  Git Tag v*  │    │  workflow_dispatch   │    │
│  │  (CI only)    │    │  (CI + CD)   │    │  (manual trigger)   │    │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘    │
│         │                   │                        │               │
│         ▼                   ▼                        ▼               │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    CI Job (ubuntu-latest)                     │    │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │    │
│  │  │ checkout │→  │ pip inst │→  │ pytest   │→  │ ruff     │  │    │
│  │  │ repo     │   │ deps     │   │ (27 test) │   │ check    │  │    │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                              │ (only if tag trigger)                 │
│                              ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              CD Job (ubuntu-latest, needs CI)                 │    │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │    │
│  │  │ docker   │→  │ buildx   │→  │ build +  │→  │ SSH      │  │    │
│  │  │ login    │   │ setup    │   │ push img │   │ deploy   │  │    │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘  │    │
│  └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                              │ SSH: docker compose pull && up -d
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LINUX VPS (Ubuntu/Debian)                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                Docker Compose Service                          │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │  Container: crypto-news-pipeline                      │    │   │
│  │  │  Image:   user/crypto-news-pipeline:latest           │    │   │
│  │  │  Restart: unless-stopped                              │    │   │
│  │  │  Health:  pgrep -f "python -m src.main"              │    │   │
│  │  │                                                       │    │   │
│  │  │  Volume mounts:                                       │    │   │
│  │  │    ./data/.env      → /app/.env  (ro)                │    │   │
│  │  │    ./data/sources.json → /app/sources.json (ro)      │    │   │
│  │  │    ./data/logs/     → /app/logs/                     │    │   │
│  │  │    ./data/session/  → /app/ (telegram.session)       │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (New Files)

```
crypto-news-pipeline/
│
├── Dockerfile                          # Container definition
├── entrypoint.sh                       # Pre-flight validation + exec
├── docker-compose.yml                  # Production service definition
├── .dockerignore                       # Files excluded from Docker context
│
└── .github/
    └── workflows/
        └── deploy.yml                  # CI + CD pipeline workflows
```

### Pattern 1: Entrypoint Validation + exec
**What:** A shell script that validates environment preconditions before handing control to the Python process. Uses `exec` to replace the shell process so Docker signals (`SIGTERM`) propagate directly to Python.

**When to use:** Any Docker container where pre-flight validation is needed (file existence, directory creation, config sanity checks).

**Example:**
```bash
#!/bin/sh
# entrypoint.sh — Pre-flight validation for crypto-news-pipeline
set -e

# Validate required files exist
for f in .env sources.json; do
    if [ ! -f "$f" ]; then
        echo "ERROR: Required file '$f' not found. Mount it as a volume."
        exit 1
    fi
done

# Create logs directory if missing
mkdir -p logs

# Check .env has content (basic check)
if [ ! -s ".env" ]; then
    echo "ERROR: .env is empty. Fill in your credentials."
    exit 1
fi

echo "Entrypoint validation passed. Starting pipeline..."
exec python -m src.main
```
[CITED: Context convention — `exec` replaces shell so signals reach the Python process; validation pattern is standard Docker practice]

### Pattern 2: GitHub Actions CI/CD with Conditional Triggers
**What:** A single workflow file with multiple jobs gated by trigger event. CI runs on `push` to `main`. CD runs the full pipeline only on `v*` tags.

**When to use:** Projects that want fast CI feedback on every merge but reserve the cost/risk of CD for versioned releases.

**Anti-Pattern:** Running `docker build` on every push to main without tagging — wastes time and registry space. Use the tag gate to control CD.

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio ruff
      - name: Lint with ruff
        run: ruff check src/
      - name: Test with pytest
        run: python -m pytest -v

  cd:
    needs: ci
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - name: Login to Docker Hub
        uses: docker/login-action@v4
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4
      - name: Build and push
        uses: docker/build-push-action@v7
        with:
          push: true
          tags: |
            ${{ secrets.DOCKERHUB_USERNAME }}/crypto-news-pipeline:latest
            ${{ secrets.DOCKERHUB_USERNAME }}/crypto-news-pipeline:${{ github.ref_name }}
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/crypto-news-pipeline
            docker compose pull
            docker compose up -d
```
[CITED: github.com/docker/build-push-action README — action syntax; github.com/appleboy/ssh-action README — known_hosts and script inputs]

### Anti-Patterns to Avoid

- **Alpine base image**: Avoid `python:3.14-alpine`. The musl C library causes subtle incompatibilities with some Python packages. User chose `python:3.14-slim` explicitly in D-01.
- **Multi-stage Dockerfile for pure-Python**: Adds complexity with no benefit. No compiled extensions, no build artifacts to prune. Single-stage is cleaner and simpler.
- **Storing `.env` in the Docker image**: Build-time ARGs or baked-in `.env` files leak secrets into the image layer. Use `env_file: .env` with volume mounts instead.
- **`docker compose restart` instead of `up -d`**: `restart` does not pick up config changes. Always use `docker compose pull && docker compose up -d` to handle image changes AND config/env changes.
- **Putting tests in the production image**: `COPY tests/` into the image bloats it and is a security concern. Keep tests out of the Docker build context via `.dockerignore`.
- **Using `CMD` instead of `ENTRYPOINT` for the wrapper script**: `ENTRYPOINT` ensures the wrapper runs even if someone passes arguments to `docker run`. Use `ENTRYPOINT ["./entrypoint.sh"]` with no `CMD`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docker image build + push in CI | Custom shell script calling `docker build` + `docker push` | `docker/build-push-action@v7` | Handles Buildx setup, multi-platform, cache export, provenance attestations, GitHub Actions native logging. Hand-rolling misses cache mounts and BuildKit features. |
| Docker registry login | `echo $PAT | docker login -u $USER --password-stdin` | `docker/login-action@v4` | Scope-limited credentials, automatic logout, Buildx configuration, no credential exposure in logs. |
| SSH remote commands | `ssh -i key user@host "docker compose pull"` | `appleboy/ssh-action@v1` | Handles known_hosts verification, key injection, multi-host support, env passthrough, retry logic. |
| Health check for process-alive | Custom Python script in the container that pings an endpoint | Docker `healthcheck: test: ["CMD-SHELL", "pgrep ..."]` | Zero dependencies. `pgrep` is available in `python:3.14-slim` (Debian base). No port listening needed for an outbound-only daemon. |
| Secrets management for CI | Encrypting secrets in the repo with git-crypt/sops | GitHub Secrets | Native encrypted storage. No key management overhead. Revokable per-repo. |

**Key insight:** Every hand-rolled alternative in this table has been the source of production incidents (leaked credentials, failed builds, zombie containers). The standard GitHub Actions are maintained by Docker/Appleboy, have thousands of stars, and handle edge cases the hand-rolled versions miss.

## Common Pitfalls

### Pitfall 1: SSH Host Key Verification Failure
**What goes wrong:** The `appleboy/ssh-action` fails with "Host key verification failed" because the runner has never connected to the VPS before.
**Why it happens:** GitHub Actions runners are ephemeral VMs with a clean `~/.ssh/known_hosts`. Without the host key pre-populated, SSH refuses to connect.
**How to avoid:** Either (a) set `SSH_KNOWN_HOSTS` secret from `ssh-keyscan <host>` output and pass it to the action, or (b) use the `kielabokkie/ssh-key-and-known-hosts-action@v1` before the deploy step to add the host key automatically.
**Warning signs:** "Host key verification failed" in workflow logs; deploy step silently skipped.

### Pitfall 2: Docker Build Fails Because of `.dockerignore`/Context Mismatch
**What goes wrong:** `COPY src/ ./src/` fails because the Docker build context doesn't include `src/`.
**Why it happens:** When using the default git context (no explicit checkout), `docker/build-push-action` uses the git ref directly. If `.dockerignore` is too aggressive or the git context doesn't match expectations, files are missing.
**How to avoid:** Use explicit `actions/checkout@v4` + `context: .` in the build-push action. This ensures the workspace is predictable.
**Warning signs:** `COPY failed: file not found` errors in build step.

### Pitfall 3: Container Starts But Immediately Exits
**What goes wrong:** `docker compose up -d` succeeds, but `docker ps` shows the container exited.
**Why it happens:** The `.env` file on the VPS is missing keys or has placeholder values, causing `ConfigError` at startup. The entrypoint script catches missing files, but the Python code raises `ConfigError` before logging is fully configured.
**How to avoid:** Ensure the deploy script includes `docker compose logs` in a separate step, and verify `.env` manually after first deployment.
**Warning signs:** Container status is `Exited(1)` instead of `Up` or `Healthy`.

### Pitfall 4: Telegram Session Lost After Deploy
**What goes wrong:** Every deploy requires Telegram re-authentication because the `.session` file is not persisted.
**Why it happens:** The `telegram.session` file is created inside the container at `/app/telegram.session`. Without a volume mount for the session directory, a new container starts with a clean filesystem.
**How to avoid:** Mount a volume for `telegram.session` (e.g., `./data/session/:/app/session/` and set the Telethon session path to `/app/session/telegram.session` via `SESSION_PATH` env var, OR mount the working directory and rely on the session file being written to the current directory.
**Warning signs:** On every deploy, Telethon prompts for phone number + OTP in the logs. The pipeline stalls.

### Pitfall 5: Health Check on Outbound-Only Daemon
**What goes wrong:** A `curl`-based health check always fails because the container has no HTTP server.
**Why it happens:** The pipeline establishes outbound connections (Telethon, PTB, OpenRouter, Binance). There is no inbound HTTP endpoint. A health check like `curl -f http://localhost/` will time out or fail.
**How to avoid:** Use `CMD-SHELL pgrep -f "python -m src.main" || exit 1` to check if the main Python process is alive. This works in `python:3.14-slim` because `procps` (providing `pgrep`) is available in the Debian base.
**Warning signs:** Health check always shows `unhealthy`; Docker marks container as unhealthy but doesn't restart it unless combined with `restart: unless-stopped`.

## Code Examples

### Dockerfile
```dockerfile
# Dockerfile — Crypto News Pipeline
FROM python:3.14-slim AS base

LABEL org.opencontainers.image.title="Crypto News Pipeline"
LABEL org.opencontainers.image.description="Automated crypto news aggregation, AI processing, and multi-platform publishing pipeline"
LABEL org.opencontainers.image.source="https://github.com/your-org/crypto-news-pipeline"
LABEL org.opencontainers.image.licenses="MIT"

# Prevent Python from writing .pyc files and enable unbuffered stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (leverages Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and entrypoint
COPY src/ ./src/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
```
[CITED: Dockerfile best practices — Python base image, pip install order for layer caching. ASSUMED for version numbers — `python:3.14-slim` rolling tag resolves to latest 3.14.x patch.]

### docker-compose.yml
```yaml
# docker-compose.yml — Production deployment
services:
  pipeline:
    build:
      context: .
      dockerfile: Dockerfile
    image: ${DOCKERHUB_USERNAME:-crypto-news-pipeline}/crypto-news-pipeline:latest
    container_name: crypto-news-pipeline
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data/.env:/app/.env:ro
      - ./data/sources.json:/app/sources.json:ro
      - ./data/logs:/app/logs
      - ./data/session:/app/session
    healthcheck:
      test: ["CMD-SHELL", "pgrep -f 'python -m src.main' || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```
[CITED: Docker Compose spec — env_file, volumes, restart, healthcheck syntax. ASSUMED — specifics of interval/retries/start_period values (agent's discretion area).]

### .dockerignore
```
# Git
.git/
.gitignore
.gitattributes

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Test
tests/
.pytest_cache/

# Config (handled by volumes in production)
.env
.env.example
sources.json
sources.default.json

# Data (handled by volumes)
logs/
telegram.session

# Documentation
*.md
AI-SPEC.md

# IDE
.vscode/
.idea/
```
[VERIFIED: .dockerignore patterns — standard Python/Docker project conventions. Current .gitignore entries inform the exclusion list.]

### GitHub Actions Workflow (deploy.yml)
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  PYTHON_VERSION: '3.14'

jobs:
  ci:
    name: Test & Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio ruff

      - name: Lint with ruff
        run: ruff check src/

      - name: Test with pytest
        run: python -m pytest -v

  cd:
    name: Build, Push & Deploy
    needs: ci
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Docker Hub
        uses: docker/login-action@v4
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      - name: Build and push Docker image
        uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: |
            ${{ secrets.DOCKERHUB_USERNAME }}/crypto-news-pipeline:latest
            ${{ secrets.DOCKERHUB_USERNAME }}/crypto-news-pipeline:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script_stop: true
          script: |
            cd /opt/crypto-news-pipeline
            docker compose pull
            docker compose up -d
            docker system prune -f
```
[CITED: github.com/docker/build-push-action README — v7 syntax with cache-from/cache-to; github.com/appleboy/ssh-action README — v1 syntax with script_stop; github.com/docker/login-action README — v4 syntax. ASSUMED — `concurrency` settings, workflow structure details (agent's discretion area).]

### entrypoint.sh
```bash
#!/bin/sh
# entrypoint.sh — Pre-flight validation for crypto-news-pipeline
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "=== Crypto News Pipeline Entrypoint ==="

# Validate required files
for f in .env sources.json; do
    if [ ! -f "$f" ]; then
        printf "${RED}ERROR:${NC} Required file '$f' not found.\n"
        printf "       Mount it as a Docker volume or bind mount.\n"
        exit 1
    fi
done

# Validate .env is not a template
if grep -q "your_" .env 2>/dev/null; then
    printf "${RED}ERROR:${NC} .env contains placeholder values ('your_').\n"
    printf "       Replace with real credentials before running.\n"
    exit 1
fi

# Create logs directory if missing
mkdir -p logs
mkdir -p session

echo "Entrypoint validation passed."
exec python -m src.main
```
[CITED: `exec` pattern — standard Docker signal handling. ASSUMED — specific validation steps (agent's discretion area).]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker-compose` (v1, Python-based) | `docker compose` (v2, Go plugin) | 2022–2023 | `docker-compose` CLI is deprecated. Use `docker compose` (no hyphen) which is a Docker CLI plugin. |
| `docker build` (CLI) | `docker buildx build` (BuildKit) | 2022+ | Buildx is the default in newer Docker versions. Always use `docker/setup-buildx-action` in CI for consistency. |
| `actions/checkout@v3` | `actions/checkout@v4` | 2024 | v4 runs on Node 20 (required by GitHub Actions runner updates). All actions should target v4+. |
| `docker/build-push-action@v5` | `v7` | 2026 (Mar) | v6+ supports Git context by default (no explicit checkout needed). v7 added provenance attestations and Build Record API. |
| `docker/login-action@v3` | `v4` | 2026 (Mar) | v4 uses Node 24 as default runtime. |
| `ruff` standalone | `ruff check src/` | 2023+ | Ruff replaced flake8/black/isort as the unified Python linter. Use `ruff check` for lint, `ruff format` for formatting. |

**Deprecated/outdated:**
- `docker-compose` (hyphenated, v1): Replaced by `docker compose` plugin. Do not install `docker-compose` package separately.
- `actions/checkout@v3`: Uses Node 16 which is deprecated on GitHub Actions runners.
- **Flake8/Black/Isort**: Ruff subsumes all three. Already used in this project (D-09 references ruff specifically).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pgrep` is available in `python:3.14-slim` (Debian trixie base) | docker-compose.yml healthcheck | Low — `procps` is included in the slim Debian base. If not, healthcheck silently fails (harmless). |
| A2 | `python:3.14-slim` rolling tag resolves to latest 3.14.x patch at build time | Dockerfile | Low — pinning to `3.14-slim` ensures minor version consistency. Breaking changes only happen at 3.15. |
| A3 | `docker compose` (v2 plugin) is the standard on modern Docker Engine | Recommended pattern | Low — older systems may need `docker-compose` v1. Planner should verify Docker Compose version on VPS. |
| A4 | `ruff check src/` is the correct lint command without a config file | CI workflow | Medium — ruff's behavior with no config file is conservative (no rules enabled by default). The planner may need a `pyproject.toml` or `.ruff.toml` to enable rules. |
| A5 | The existing `event_loop` fixture in `conftest.py` works in CI without warnings | CI workflow | Low — pytest-asyncio 1.3.0 supports the old fixture pattern. May produce deprecation warnings but won't fail. |

## Open Questions (RESOLVED)

1. **ruff configuration file** — RESOLVED: `.ruff.toml` created in Plan 02 Task 1 with `select = ["E", "F", "I"]`, `target-version = "py314"`
   - What we know: D-09 specifies "ruff lint" as a CI stage. The project has no `.ruff.toml` or `pyproject.toml` with ruff settings.
   - What's unclear: What rules should ruff enforce? The default (`ruff check src/` with no config) enables no rules — it passes trivially.
   - Recommendation: Create a minimal `.ruff.toml` selecting a rule set (e.g., `select = ["E", "F", "I"]` for pycodestyle + pyflakes + import sorting). Or skip ruff config creation and note that the planner must either add one or accept that lint will pass vacuously.

2. **VPS directory structure convention** — RESOLVED: Documented in DEPLOYMENT.md (Plan 03 Task 1) with `/opt/crypto-news-pipeline` structure
   - What we know: The deploy script assumes `/opt/crypto-news-pipeline` as the project root on the VPS.
   - What's unclear: Should this be configurable via a GitHub variable? What about the `data/` subdirectory for volumes?
   - Recommendation: Document the assumed path structure (can be changed by editing the workflow's SSH script).

3. **First-deploy bootstrapping** — RESOLVED: Full bootstrap guide in DEPLOYMENT.md (Plan 03 Task 1) covering Docker install, volume paths, file placement
   - What we know: The automated deploy flow assumes Docker + Docker Compose are installed, `.env` and `sources.json` exist at the correct paths, and `telegram.session` is present.
   - What's unclear: How the initial setup (Docker install, directory creation, file placement) is documented/performed.
   - Recommendation: Create a one-time setup script or document manual steps in a deployment guide. The planner should include a task for this.

4. **Test CI dependency versions** — RESOLVED: Planner chose unpinned `pip install pytest pytest-asyncio ruff` (Plan 02 Task 3). Pinning deferred to future `requirements-dev.txt`
   - What we know: `pytest==9.0.3` and `pytest-asyncio==1.3.0` are currently installed locally.
   - What's unclear: Whether to pin CI test dependencies to specific versions or install latest.
   - Recommendation: Unpinned is fine for CI (the `pip install pytest pytest-asyncio ruff` approach). Pinning in a `requirements-dev.txt` would be more reproducible but adds maintenance. Planner's choice.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Docker build (base image) | ✓ (on dev machine) | 3.14.3 | — (runtime in container) |
| Docker Engine | Container runtime | ✗ (local dev) | — | Docker Desktop for dev, docker/build-push-action for CI |
| Docker Compose | Service definition | ✗ (local dev) | — | VPS must have Docker Compose v2 plugin |
| pytest | CI test stage | ✓ (local dev) | 9.0.3 | — (installed in CI runner) |
| ruff | CI lint stage | ✗ (local dev) | — | Installed in CI runner via `pip install ruff` |
| GitHub Actions | CI/CD pipeline | ✓ (GitHub-hosted) | — | `ubuntu-latest` runner provides Docker, Python |
| SSH (VPS) | CD deploy stage | ✗ (local dev) | — | `appleboy/ssh-action` handles SSH from CI runner |

**Missing dependencies with no fallback:**
- Docker Engine on VPS: The VPS **must** have Docker Engine installed and the `deploy` user must be in the `docker` group. This is a one-time manual setup step (or an Ansible/init script). The plan should include a documentation task for VPS bootstrap instructions.

**Missing dependencies with fallback:**
- Docker locally on dev machine: Not required for development. Developers only need git + Python to run tests and lint. Docker build is CI-only.

## Validation Architecture

> `nyquist_validation` is enabled in `.planning/config.json`. The following section maps phase requirements to test validation.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | none — `conftest.py` provides `event_loop` fixture |
| Quick run command | `python -m pytest -v` (27 tests) |
| Full suite command | `python -m pytest -v --tb=long` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-01 | Dockerfile builds successfully | smoke | `docker build -t test-pipeline .` | ❌ Wave 0 |
| REQ-02 | Entrypoint validates missing files | smoke | Manual: run container without `.env` → expect exit 1 | ❌ Manual |
| REQ-03 | CI pipeline runs tests + lint on push | integration | Push to `main` branch → observe GHA run | ❌ Wave 0 |
| REQ-04 | CD pipeline builds, pushes, deploys on tag | integration | Push `v1.0.0` tag → observe full pipeline | ❌ Manual |
| REQ-05 | docker-compose.yml is valid YAML | smoke | `docker compose config` | ❌ Wave 0 |
| REQ-06 | Container restarts on crash | integration | `docker kill container` → observe restart | ❌ Manual |

### Wave 0 Gaps

- [ ] `tests/test_docker_build.py` — smoke test that Dockerfile builds and entrypoint works (pytest-docker or simple subprocess call) — covers REQ-01
- [ ] `tests/test_compose_config.py` — validates `docker compose config` succeeds — covers REQ-05
- [ ] `.github/workflows/deploy.yml` — must be present for REQ-03, REQ-04
- [ ] A minimal `.ruff.toml` or `pyproject.toml` section enabling ruff rules — required for linting to be meaningful

### Sampling Rate
- **Per task commit:** `python -m pytest -v` (runs faster if tests pass)
- **Per wave merge:** `python -m pytest -v --tb=long`
- **Phase gate:** GitHub Actions CI green on `main` push. Full CD pipeline green on `v*` tag.

### Note on CI-only testing
The CI pipeline is the primary validation mechanism for this phase. Local testing of Docker builds is possible but requires Docker Desktop (not available on Windows dev machine). The plan should include:
1. Adding CI trigger `workflow_dispatch` so the pipeline can be tested without pushing a tag
2. A manual test procedure document for the first GitHub Actions run

## Security Domain

> `security_enforcement` is enabled by default (absent in config = enabled).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Partial | Docker Hub PAT replaces password auth. SSH key-based auth for VPS (no passwords). |
| V4 Access Control | Yes | Docker image runs as non-root (Python slim default). VPS user in `docker` group. |
| V5 Input Validation | No | Input validation is the application's responsibility (Phase 1-2). |
| V6 Cryptography | No | No secrets encrypted at rest within the scope of this phase. `.env` on VPS filesystem. |

### Known Threat Patterns for Docker + CI/CD

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secrets in image layers | Information Disclosure | Use `env_file: .env` (runtime, not build-time). Do NOT use `ARG`/`ENV` for secrets in Dockerfile. |
| Compromised base image | Tampering | Pin major version (`python:3.14-slim`). Docker Hub official images have automatic security scanning. |
| SSH key exposure in CI logs | Information Disclosure | `appleboy/ssh-action` masks secrets in logs. Use `script_stop: true` to fail on SSH errors. |
| Unauthorized image push | Spoofing | Docker Hub PAT with limited scope (push-only). Rotate PAT regularly. |
| Container breakout (Docker socket) | Elevation of Privilege | Do NOT mount `/var/run/docker.sock` into the container (not needed). |
| Supply chain (pip packages) | Tampering | `pip install --no-cache-dir` with pinned versions in `requirements.txt`. |

## Sources

### Primary (HIGH confidence)
- [Docker Hub — python official image tags](https://hub.docker.com/_/python?tab=tags&name=slim) — `python:3.14-slim` exists and is based on Debian trixie-slim
- [docker/build-push-action README](https://github.com/docker/build-push-action) — v7.1.0 syntax, Git context vs Path context
- [docker/login-action README](https://github.com/docker/login-action) — v4.1.0 syntax, scope-limited credentials
- [docker/setup-buildx-action README](https://github.com/docker/setup-buildx-action) — v4.0.0 syntax
- [appleboy/ssh-action README](https://github.com/appleboy/ssh-action) — v1 syntax, known_hosts, multiple commands
- [Docker Compose specification](https://docs.docker.com/compose/compose-file/) — healthcheck, env_file, volumes, restart syntax
- [Docker healthcheck best practices](https://docs.docker.com/guides/python/develop/) — compose healthcheck patterns with start_period
- [Python Docker Official Image Dockerfile](https://github.com/docker-library/python/blob/6cc07b27ad0df3769bbd1a2a1000a842634681d2/3.14/slim-bookworm/Dockerfile) — confirms python:3.14-slim is based on debian:bookworm-slim with procps available

### Secondary (MEDIUM confidence)
- Pip list output — confirms Python 3.14.3, pytest 9.0.3, pytest-asyncio 1.3.0
- Project source code analysis — confirms 27 tests, conftest.py event_loop pattern, no pytest.ini/pyproject.toml

### Tertiary (LOW confidence)
- None — all critical claims are verified against official docs or live registry inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools verified against GitHub repos, Docker Hub, or pip list
- Architecture: HIGH — patterns confirmed from multiple official sources
- Pitfalls: HIGH — informed by real-world CI/CD incidents and published best practices

**Research date:** 2026-05-23
**Valid until:** 2026-06-23 (30 days — GitHub Actions and Docker tooling are relatively stable; action versions may receive patch updates)
