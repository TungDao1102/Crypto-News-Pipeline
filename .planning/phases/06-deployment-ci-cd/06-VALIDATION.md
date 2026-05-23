---
phase: 6
slug: deployment-ci-cd
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-23
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | none — `conftest.py` provides `event_loop` fixture |
| **Quick run command** | `python -m pytest -v` (27 tests) |
| **Full suite command** | `python -m pytest -v --tb=long` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -v`
- **After every plan wave:** Run `python -m pytest -v --tb=long`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | REQ-01 | — | N/A — shell script | smoke | `test -f entrypoint.sh && head -1 entrypoint.sh | grep -q "#!/bin/sh"` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | REQ-01 | — | N/A — config file | smoke | `test -f .dockerignore && grep -q ".env" .dockerignore` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | REQ-01 | T-6-01 | Secrets not baked into image | smoke | `docker build -t test-pipeline .` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | REQ-05 | — | N/A — lint config | unit | `python -c "import tomllib; data = tomllib.load(open('.ruff.toml','rb')); assert 'E' in data.get('lint',{}).get('select',[])"` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | REQ-05 | — | N/A — compose config | smoke | `docker compose config` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 1 | REQ-03, REQ-04 | T-6-02 | SSH key protection in CI | integration | Push to `main` or tag `v*` → observe GHA run | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | REQ-06 | — | N/A — docs | manual | Manual: follow DEPLOYMENT.md steps | ❌ Wave 2 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_docker_build.py` — smoke test that Dockerfile builds and entrypoint works (simple subprocess call)
- [ ] `tests/test_compose_config.py` — validates `docker compose config` succeeds
- [ ] `.github/workflows/deploy.yml` — CI/CD workflow must be present
- [ ] `.ruff.toml` — minimal ruff configuration enabling rules

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CD pipeline runs on tag | REQ-04 | Requires pushing a `v*` tag to GitHub | Push `v1.0.0-test` tag, observe GitHub Actions run full pipeline |
| Container restart on crash | REQ-06 | Requires Docker Engine on production-like system | `docker kill <container>`, verify `docker ps` shows running state |
| Secrets not baked into image | REQ-01 | Requires reviewing Dockerfile | Verify `.env` is not in `COPY` or `ADD` instructions; check `.dockerignore` includes `.env` |
| Entrypoint validates missing files | REQ-02 | Requires interactive failure mode | Run container without `.env` mount, verify exit code 1 with clear error message |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
