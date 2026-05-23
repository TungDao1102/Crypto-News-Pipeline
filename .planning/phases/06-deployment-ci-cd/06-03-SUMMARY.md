# Plan 06-03 — VPS Bootstrap Guide — Summary

## Objective
Create DEPLOYMENT.md documenting the complete VPS setup, GitHub Secrets configuration, first-deploy procedure, troubleshooting, and recovery procedures.

## Tasks Completed

### Task 1: DEPLOYMENT.md
- 210 lines, valid markdown
- **Sections:**
  - **Prerequisites** — Linux VPS, sudo, Git, Docker Hub account
  - **VPS Initial Setup** — docker engine + compose plugin install commands, user setup, repo clone
  - **Directory Structure** — `/opt/crypto-news-pipeline/` layout with `data/` subdirectories
  - **Files You Need to Create** — `.env` (8 env vars table with descriptions) and `sources.json` placement, `chmod 600`
  - **GitHub Secrets Configuration** — 6 secrets table with how-to-obtain for each (DOCKERHUB_USERNAME, DOCKERHUB_TOKEN, SSH_HOST, SSH_USER, SSH_PRIVATE_KEY, SSH_KNOWN_HOSTS)
  - **First Deploy** — 6-step procedure ending with `git tag v1.0.0 && git push origin v1.0.0`
  - **Verification** — `docker ps`, `docker compose logs`, grep for entrypoint message
  - **Troubleshooting** — container exits (missing env vars), session lost (volume mount), SSH key (known_hosts), health check (informational)
  - **Recovering Telegram Session** — interactive auth flow via `docker compose run --rm pipeline`
  - **Updating** — tag-and-push workflow
  - **Rolling Back** — manual image tag pinning
- No real credentials; angle-bracket placeholders throughout
- References exact paths from docker-compose.yml and exact secret names from deploy.yml
- **Commit:** `fe46cf2`

## Verification
- All required sections verified present via automated grep
- References: DOCKERHUB_USERNAME, SSH_HOST, /opt/crypto-news-pipeline, docker compose
- Line count >= 80 (210 lines)
- Test suite: 27/27 passed

## Key Decisions
- SSH_KNOWN_HOSTS documented as optional but recommended
- Telegram session recovery documented as interactive `docker compose run --rm` flow (cannot be fully automated per Telethon auth model)
- Rolling back documented as manual docker-compose.yml edit (no CI/CD rollback automation)
