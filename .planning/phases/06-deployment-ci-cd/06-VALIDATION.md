---
phase: 06
slug: deployment-ci-cd
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-23
updated: 2026-05-24
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | none — `conftest.py` provides `event_loop` fixture |
| **Quick run command** | `python -m pytest tests/test_devops.py -v -q` |
| **Full suite command** | `python -m pytest tests/ -v -q` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_devops.py -v -q`
- **After every plan wave:** Run `python -m pytest tests/ -v -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test | Status |
|---------|------|------|-------------|------|--------|
| 06-01-01 | 01 | 1 | REQ-01 — Dockerfile | `TestDockerfile` (9) | ✅ green |
| 06-01-02 | 01 | 1 | REQ-01 — entrypoint.sh | `TestEntrypoint` (8) | ✅ green |
| 06-01-03 | 01 | 1 | REQ-01 — .dockerignore | `TestDotDockerignore` (5) | ✅ green |
| 06-02-01 | 02 | 1 | REQ-05 — .ruff.toml | `TestRuffToml` (4) | ✅ green |
| 06-02-02 | 02 | 1 | REQ-05 — docker-compose.yml | `TestDockerCompose` (6) | ✅ green |
| 06-02-03 | 02 | 1 | REQ-03, REQ-04 — deploy.yml CI/CD | `TestDeployWorkflow` (8) | ✅ green |
| 06-03-01 | 03 | 2 | REQ-06 — DEPLOYMENT.md docs | `TestDEPLOYMENT` (5) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_devops.py` — 46 smoke tests for all DevOps artifacts (Dockerfile, entrypoint, dockerignore, ruff config, compose, CI/CD workflow, deployment docs)
- [x] `.github/workflows/deploy.yml` — CI/CD workflow present
- [x] `.ruff.toml` — minimal ruff configuration enabling rules

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docker build` succeeds | REQ-01 | Requires Docker Engine | `docker build -t test-pipeline .` in project root |
| `docker compose config` succeeds | REQ-05 | Requires Docker Compose | `docker compose config` validates compose file |
| Container restart on crash | REQ-06 | Requires Docker Engine on production-like system | `docker kill <container>`, verify `docker ps` shows running state |
| Secrets not baked into image | REQ-01 | Requires reviewing Dockerfile | Verify `.env` is not in `COPY` or `ADD` instructions; check `.dockerignore` includes `.env` |
| Entrypoint validates missing files | REQ-02 | Requires interactive failure mode | Run container without `.env` mount, verify exit code 1 with clear error message |
| CD pipeline runs on tag push | REQ-04 | Requires pushing a `v*` tag to GitHub | Push `v1.0.0-test` tag, observe GitHub Actions run full pipeline |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** auto (all artifacts verified by CI pipeline + local syntax tests)
