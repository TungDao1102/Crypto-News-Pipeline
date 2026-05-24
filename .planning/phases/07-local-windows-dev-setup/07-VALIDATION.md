---
phase: 07
slug: local-windows-dev-setup
status: validated
nyquist_compliant: true
created: 2026-05-24
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | none |
| **Quick run command** | `python -m pytest tests/test_run_ps1.py -v -q` |
| **Full suite command** | `python -m pytest tests/ -v -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_run_ps1.py -v -q`
- **After every plan wave:** Run `python -m pytest tests/ -v -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test | Status |
|---------|------|------|-------------|------|--------|
| 07-01-01 | 01 | 1 | D-01 — PowerShell (.ps1) format | `test_exists`, `test_ps1_extension` | ✅ green |
| 07-01-02 | 01 | 1 | D-02 — Python installed check (Get-Command) | `test_python_installed_check` | ✅ green |
| 07-01-03 | 01 | 1 | D-07 — Python version 3.14 check | `test_python_version_check` | ✅ green |
| 07-01-04 | 01 | 1 | D-05, D-06 — Auto-create venv if missing | `test_venv_auto_create`, `test_venv_path_constructed` | ✅ green |
| 07-01-05 | 01 | 1 | D-04 — Auto-install dependencies (pip install) | `test_pip_install` | ✅ green |
| 07-01-06 | 01 | 1 | D-08, D-12 — .gitignore safeguarding | `test_gitignore_modification` | ✅ green |
| 07-01-07 | 01 | 1 | D-09 — No duplicated validation (no grep/your_) | `test_no_duplicated_validation` | ✅ green |
| 07-01-08 | 01 | 1 | D-10 — No directory pre-creation | `test_no_dir_precreation_logs`, `test_no_dir_precreation_via_newitem` | ✅ green |
| 07-01-09 | 01 | 1 | D-14, D-15 — --help and --setup flags | `test_has_help_switch`, `test_has_setup_switch` | ✅ green |
| 07-01-10 | 01 | 1 | D-13 — Pipeline start (python -m src.main) | `test_pipeline_start_cmd` | ✅ green |
| 07-01-11 | 01 | 1 | D-11, D-03 — Session in .session/ (no symlink) | `test_session_referenced` | ✅ green |
| 07-01-12 | 01 | 1 | D-12 — .session/ in .gitignore | `TestGitignore::test_session_dir_ignored` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_run_ps1.py` — 23 tests covering all 15 decisions (D-01 through D-15)
- [x] `.session/` added to `.gitignore` under `# Project-specific`
- [x] `.venv/` confirmed present in `.gitignore` under `# Environments`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `.\run.ps1 --help` displays usage and exits 0 | D-14 | Requires PowerShell execution | Open PowerShell in project root, run `.\run.ps1 --help`, verify usage text shown, exit code 0 |
| `.\run.ps1 --setup` creates .venv + installs deps | D-15 | Requires Python 3.14 installed | Run `.\run.ps1 --setup`, verify .venv/ created, pip install runs, no pipeline start |
| `.\run.ps1` (no flags) starts full pipeline | D-13 | Requires .env + sources.json with valid credentials | Run `.\run.ps1`, verify pipeline starts or config.py ConfigError with clear message |
| Missing Python exits with helpful message | D-02 | Requires Python removed from PATH | Temporarily remove Python from PATH, run `.\run.ps1`, verify message points to python.org |
| PowerShell syntax valid | D-01 | Requires PowerShell 5.1+ | Run `[System.Management.Automation.Language.Parser]::ParseFile("run.ps1", [ref]$null, [ref]$null)` |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 3s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** auto (all 15 decisions verified by smoke tests)
