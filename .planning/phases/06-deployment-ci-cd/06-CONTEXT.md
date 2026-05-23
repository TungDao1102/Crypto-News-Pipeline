# Phase 6: Deployment & CI/CD - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Containerize the pipeline, automate builds and deploys via CI/CD, and establish a production-ready deployment on a Linux VPS. The phase covers Dockerfile creation, docker-compose configuration, GitHub Actions pipeline, and secrets/config management for production. No new pipeline features — only getting the existing 5-phase pipeline running reliably in production.

</domain>

<decisions>
## Implementation Decisions

### Container Strategy
- **D-01:** Docker containerization with `python:3.14-slim` base image. No Alpine (avoid musl/glibc risk).
- **D-02:** Single-stage Dockerfile (no multi-stage needed — all deps are pure Python).
- **D-03:** Entrypoint shell script (`entrypoint.sh`) that validates environment, creates required dirs, then runs `python -m src.main`.
- **D-04:** Standard Dockerfile pattern: `COPY requirements.txt` → `pip install` → `COPY src/`. Leverages Docker layer caching.
- **D-05:** Mounted volumes for `.env`, `sources.json`, `logs/`, and Telegram `.session` file. Session persistence avoids re-auth on every restart.

### CI/CD Platform & Flow
- **D-06:** GitHub Actions as CI/CD platform.
- **D-07:** Trigger strategy: push to `main` runs test + lint (CI). Git tag (`v*`) triggers full pipeline: test → lint → build image → push to Docker Hub → SSH deploy.
- **D-08:** Deploy via SSH into VPS: `docker compose pull && docker compose up -d`.
- **D-09:** Full pipeline stages: pytest, ruff lint, docker buildx, push to Docker Hub, SSH remote deploy.
- **D-10:** Docker Hub as container registry (public image).

### Deployment Target & Process Management
- **D-11:** Linux VPS as deployment target (Ubuntu/Debian recommended).
- **D-12:** Docker `restart: unless-stopped` policy for crash recovery and auto-start on boot.
- **D-13:** `docker compose` for declarative service definition (volumes, env_file, restart policy, healthcheck).
- **D-14:** Docker health check configured in compose — basic process-alive check.

### Secrets & Config in Deployment
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### System Architecture
- `AI-SPEC.md` — Full architecture, data flow, module responsibilities. Understanding the pipeline structure is essential to design the Dockerfile and deployment config.
- `requirements.txt` — Current Python dependencies (5 packages). Base for Dockerfile pip install.
- `.env.example` — Template for all 8 required environment variables.

### Prior Phase Contracts
- `.planning/phases/05-resilience-logging-monitoring/05-CONTEXT.md` — D-11 (human-readable logging, no JSON aggregation), D-12 (config-driven log levels), D-14 (50MB×10 rotation). Informs logging strategy in production container.
- `.planning/phases/04-publisher/04-CONTEXT.md` — Publishing patterns, Binance/Bot API usage (outbound connections).
- `.planning/phases/03-bot-reviewer/03-CONTEXT.md` — Bot wiring, PTB polling (long-running process requirement).
- `.planning/phases/02-ai-handler/02-CONTEXT.md` — AIConsumer pattern, OpenRouter API usage.
- `.planning/phases/01-configuration-crawler/01-CONTEXT.md` — Telethon session management, source config.

### Existing Code
- `src/config.py` — Config loading logic, REQUIRED_KEYS (8 env vars). Deployment must ensure all are present.
- `src/main.py` — Entry point (`python -m src.main`), asyncio event loop, signal handlers.
- `src/logging_setup.py` — `RotatingFileHandler` config (50MB×10). Logs to `logs/` directory.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/main.py` — Entry point is `if __name__ == "__main__": asyncio.run(main())`. Simple module invocation works for `python -m src.main` inside container.
- `src/config.py` — Validates all secrets on startup with helpful error messages. Container entrypoint can rely on this for early failure.
- `.gitignore` — Already ignores `.env`, `logs/`, `sources.json`, `telegram.session`. No changes needed.

### Established Patterns
- All config via `.env` + `sources.json` — deployment pattern is to mount these as volumes.
- Long-running asyncio daemon with Telethon + PTB polling — no web server, no REST API. Container doesn't need port mapping.
- Logging to `logs/` directory via `RotatingFileHandler` — must persist this directory across restarts.
- Clean shutdown via signal handlers — Docker `SIGTERM` → `shutdown()` → graceful exit.

### Integration Points
- **Root directory** — `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `entrypoint.sh` all go in project root.
- **`.github/workflows/`** — New directory needed for GitHub Actions workflow YAML.
- **`.gitignore`** — Should add `.env` if not already there (currently gitignored). May need to add `.dockerignore`.
- **VPS server** — Requires Docker Engine + Docker Compose plugin + git (for initial clone).

</code_context>

<specifics>
## Specific Ideas

- Entrypoint script should validate that `.env` and `sources.json` exist, then exec `python -m src.main` to properly handle signals
- Docker health check: `CMD python -c "import sys; sys.exit(0)"` or `CMD pgrep python3 || exit 1` — simple process check
- No port exposure needed — all integrations (Telethon, PTB, OpenRouter, Binance Square) establish outbound connections
- Image tag strategy: `latest` for default deploy, `vX.Y.Z` for versioned releases, commit SHA for dev builds

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-deployment-ci-cd*
*Context gathered: 2026-05-23*
