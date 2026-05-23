# Project Roadmap — Crypto News & Airdrop Automation Pipeline

## Phase 1: Configuration & Crawler ✅
- Status: Executed (UAT partial)
- Plans: Implementation complete. 16 tests defined in `01-UAT.md`, 1 confirmed.

## Phase 2: AI Handler & Processing 📋
- Status: Planned (4 plans, 17 decisions covered)
- Plans:
  - `02-01-PLAN.md` — DraftContent model + httpx dependency (Wave 1)
  - `02-02-PLAN.md` — Text preprocessor + rate limiter + worker scaffold (Wave 1)
  - `02-03-PLAN.md` — OpenRouter API caller + 2-stage processing + prompt registry (Wave 2)
  - `02-04-PLAN.md` — Wire AI handler into main.py (Wave 2)

## Phase 3: Bot Reviewer & Mode Management ✅
- Status: Shipped — PR #2
- Plans:
  - `03-PLAN.md` — 5 plans in 2 waves
  - Plan 01: Bot Setup & SystemState (Wave 1)
  - Plan 02: Command Handlers (Wave 2)
  - Plan 03: Approval Flow (Wave 2)
  - Plan 04: Edit Flow (Wave 2)
  - Plan 05: AUTO Mode & Guardrails (Wave 2)

## Phase 4: Publisher & Platform Integration ✅
- Status: Shipped — PR #3
- Decisions: 6 areas discussed, 6 decisions captured in `04-CONTEXT.md`

## Phase 5: Resilience, Logging & Monitoring ✅
- Status: Shipped — PR #5
- Plans:
  - `05-01-PLAN.md` — HealthCollector + alert cooldown (Wave 1)
  - `05-02-PLAN.md` — BoundedQueue + DeadLetterQueue (Wave 1)
  - `05-03-PLAN.md` — DailyMetrics collector (Wave 1)
  - `05-04-PLAN.md` — Logging config + error codes (Wave 1)
  - `05-05-PLAN.md` — AIConsumer cooldown mechanism (Wave 1)
  - `05-06-PLAN.md` — Module wiring: health callbacks, /health command, alerts, error codes, metrics wiring (Wave 2)

### Phase 6: Deployment & CI/CD ✅

**Goal:** Containerize the pipeline, automate builds and deploys via CI/CD, and establish a production-ready deployment on a Linux VPS.
**Requirements**: None specified
**Depends on:** Phase 5
**Plans:** 3 plans

Plans:
- [ ] `06-01-PLAN.md` — Container image definition (Dockerfile, entrypoint.sh, .dockerignore)
- [ ] `06-02-PLAN.md` — CI/CD & service orchestration (docker-compose.yml, GitHub Actions workflow, .ruff.toml)
- [ ] `06-03-PLAN.md` — Deployment bootstrap guide (DEPLOYMENT.md with VPS setup, secrets, and first-deploy instructions)

### Phase 7: Local Windows Development Setup

**Goal:** Create a single PowerShell script (run.ps1) that enables running the crypto-news-pipeline natively on Windows without Docker. Automate Python environment setup, dependency installation, and pipeline execution.
**Requirements**: None specified
**Depends on:** Phase 6
**Plans:** 1 plan

Plans:
- [ ] `07-PLAN.md` — Single run.ps1 script with Validate→Init→Run lifecycle, .gitignore update for .session/
