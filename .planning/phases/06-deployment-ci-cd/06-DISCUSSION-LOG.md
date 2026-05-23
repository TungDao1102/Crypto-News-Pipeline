# Phase 6: Deployment & CI/CD - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 06-deployment-ci-cd
**Areas discussed:** Container strategy, CI/CD platform & flow, Deployment target & process mgmt, Secrets & config in deployment

---

## Container Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Docker (Recommended) | Standard for Python apps. One Dockerfile, multi-stage if needed. Easy CI/CD integration, consistent env across dev/staging/prod. | ✓ |
| Bare metal / venv | pip install on the server, run via systemd/Python directly. Simpler but no image pinning. | |

**User's choice:** Docker
**Notes:** Wants reproducibility and CI/CD integration.

| Option | Description | Selected |
|--------|-------------|----------|
| python:3.14-slim (Recommended) | ~120MB, apt only what's needed. Telethon + httpx + ptb don't need build deps. | ✓ |
| python:3.14-alpine | ~50MB but slower pip install (musl compilation). Risk of subtle Alpine glibc incompatibilities. | |

**User's choice:** python:3.14-slim
**Notes:** No compiled extensions needed, slim is the safer choice.

| Option | Description | Selected |
|--------|-------------|----------|
| Single-stage (Recommended) | Single FROM. Simpler Dockerfile, enough for pure-Python apps. Build and run in same stage. | ✓ |
| Multi-stage | Separate build + runtime stages. Helps if future deps need compilation (C-extensions). Adds complexity. | |

**User's choice:** Single-stage
**Notes:** All deps are pure Python, no need for multi-stage.

| Option | Description | Selected |
|--------|-------------|----------|
| CMD python -m src.main | Simple module invocation. .env mounted as volume, logs/ as volume for persistence. | |
| Entrypoint script | wrapper.sh that validates env, creates dirs, then runs. More robust but adds a file. | ✓ |

**User's choice:** Entrypoint script
**Notes:** Wants validation before running.

| Option | Description | Selected |
|--------|-------------|----------|
| Copy src/ + requirements.txt (Recommended) | Standard pattern. COPY requirements.txt && pip install, then COPY src/. Keeps layer caching for deps. | ✓ |
| Copy entire project | Simpler but invalidates pip layer on any project file change. Also copies tests/ into image. | |

**User's choice:** Copy src/ + requirements.txt
**Notes:** Standard layer caching approach.

| Option | Description | Selected |
|--------|-------------|----------|
| .env + sources.json + logs/ (Recommended) | .env for secrets, sources.json for channel config, logs/ for log files + metrics. All mounted as volumes. | ✓ |
| .env + logs/ only | sources.json bundled in image. Simpler but requires rebuild to change sources. | |

**User's choice:** .env + sources.json + logs/
**Notes:** All runtime data persisted as volumes.

| Option | Description | Selected |
|--------|-------------|----------|
| Mount as volume (Recommended) | Persists session across restarts. Avoids re-auth on every deploy. | ✓ |
| Regenerate each time | Simpler but requires auth flow on every container start. | |

**User's choice:** Mount Telegram session as volume
**Notes:** Avoids re-auth on every deploy.

---

## CI/CD Platform & Flow

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Actions (Recommended) | Native to GitHub, free for public repos. Large ecosystem of actions for Docker build/push, SSH deploy. | ✓ |
| Other (GitLab CI, Jenkins, etc.) | Would need additional infrastructure. Only makes sense if you already use another platform. | |

**User's choice:** GitHub Actions
**Notes:** Repo is on GitHub, natural fit.

| Option | Description | Selected |
|--------|-------------|----------|
| Push to main + version tag (Recommended) | Push to main runs test + lint. Git tag (v*) triggers build + deploy. Clean separation of CI vs CD. | ✓ |
| Push to any branch | Runs full pipeline on every push. More feedback but more runs. Risk of accidental deploys from topic branches. | |

**User's choice:** Push to main + version tag
**Notes:** CI on main push, CD on version tag.

| Option | Description | Selected |
|--------|-------------|----------|
| SSH + docker compose pull/up (Recommended) | GitHub Actions SSHes into the VPS, pulls new image, restarts container. Simple, battle-tested. | ✓ |
| Self-hosted runner on VPS | Runner installed on VPS, executes deploy jobs locally. Avoids SSH key management but more infra to maintain. | |

**User's choice:** SSH + docker compose pull/up
**Notes:** Simple and battle-tested approach.

| Option | Description | Selected |
|--------|-------------|----------|
| test + lint + build + push + deploy (Recommended) | Full pipeline: pytest, ruff lint, docker build & push to registry, SSH deploy. Catches issues before deploy. | ✓ |
| build + push + deploy only | Skip tests/lint in CI — assumes pre-commit handles it. Faster but less safety net. | |

**User's choice:** Full pipeline (test + lint + build + push + deploy)
**Notes:** Wants safety net.

| Option | Description | Selected |
|--------|-------------|----------|
| Docker Hub (Recommended) | Free public repos. docker/build-push-action supports it natively. Pullable from any VPS. | ✓ |
| GitHub Container Registry (ghcr.io) | Integrated with GitHub. Free for public repos. Good alternative if you prefer staying in GitHub ecosystem. | |

**User's choice:** Docker Hub
**Notes:** Standard choice, works with any VPS.

---

## Deployment Target & Process Management

| Option | Description | Selected |
|--------|-------------|----------|
| Linux VPS (Recommended) | Any Linux VPS (Ubuntu/Debian). Docker installed, compose deploy via SSH. Typical $5-10/mo tier is enough. | ✓ |
| Other (home server, cloud VM, etc.) | If you have existing infrastructure, happy to adapt. | |

**User's choice:** Linux VPS
**Notes:** Standard VPS deployment.

| Option | Description | Selected |
|--------|-------------|----------|
| Docker restart policy (Recommended) | Docker's --restart unless-stopped handles crashes and reboots. Simplest approach for a single-container app. | ✓ |
| systemd + docker | systemd unit that manages docker start/stop. Adds logging to journald. Useful if you need pre/post hooks. | |

**User's choice:** Docker restart policy
**Notes:** Simplest for single-container app.

| Option | Description | Selected |
|--------|-------------|----------|
| docker compose (Recommended) | docker-compose.yml defines env_file, volumes, restart policy, ports. One command to start/stop. Future-proof if you add more services. | ✓ |
| docker run | Simpler for a single container. But all config on CLI — harder to version-control. | |

**User's choice:** docker compose
**Notes:** Declarative, version-controllable.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, simple health check (Recommended) | docker-compose healthcheck: test if process is running. The app already has a HealthCollector — can expose via a small HTTP health endpoint or just check PID. | ✓ |
| No health check | Rely on Docker restart policy only. If process hangs (not crashes), restart policy won't help. | |

**User's choice:** Yes, simple health check
**Notes:** Wants basic process health monitoring.

---

## Secrets & Config in Deployment

| Option | Description | Selected |
|--------|-------------|----------|
| .env file on server + GitHub Secrets (Recommended) | .env file placed on the VPS manually (or via GitHub Secrets → SSH scp on first deploy). sources.json via volume. | ✓ |
| All through GitHub Secrets | Each env var stored as GitHub secret, injected into .env during CI deploy step. More automated but each secret change requires CI run. | |

**User's choice:** .env file on server + GitHub Secrets
**Notes:** Simpler secret management. GitHub Secrets only for CI/CD credentials.

| Option | Description | Selected |
|--------|-------------|----------|
| No — gitignored (Recommended) | .env already gitignored. sources.json is also gitignored. .env.example committed as template. Keeps secrets out of git history. | ✓ |
| .env encrypted | Use git-crypt or sops to encrypt .env in repo. Adds key management overhead. | |

**User's choice:** No — gitignored
**Notes:** Standard approach, no encryption overhead needed.

| Option | Description | Selected |
|--------|-------------|----------|
| env_file: .env + volumes for sources.json (Recommended) | docker-compose.yml uses env_file: .env and volumes: ./sources.json:/app/sources.json. Standard, transparent. | ✓ |
| docker secrets | Docker swarm secrets. Adds complexity — not justified for single-container VPS deployment. | |

**User's choice:** env_file: .env + volumes for sources.json
**Notes:** Standard docker-compose pattern.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep RotatingFileHandler on volume (Recommended) | Logs go to mounted volume, persisted across restarts. Existing 50MB×10 rotation. | ✓ |
| Add container stdout + Docker log driver | App logs to stdout + Docker captures to json-file driver. Simpler for docker logs. Would need to modify logging_setup.py. | |

**User's choice:** Keep RotatingFileHandler on volume
**Notes:** Consistent with Phase 5 D-11 decision (no JSON/aggregation pipeline).

---

## the agent's Discretion

- Exact Docker health check command and interval/retries
- Entrypoint script implementation details
- Dockerfile labels, maintainer metadata
- GitHub Actions workflow names and job structure
- Docker Compose version and structure
- SSH key management approach in GitHub Actions
- Docker Hub image naming convention
- Port exposure (none needed)

## Deferred Ideas

None — discussion stayed within phase scope.
