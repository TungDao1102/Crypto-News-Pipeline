# Phase 7: Local Windows Development Setup - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable running the crypto-news-pipeline natively on Windows without Docker. Create a single PowerShell script (run.ps1) that automates Python environment setup, dependency installation, and pipeline execution — providing a fast local dev loop on Windows.

</domain>

<decisions>
## Implementation Decisions

### Run Script Format
- **D-01:** PowerShell (.ps1) as the script format. Modern Windows shell with proper error handling.
- **D-02:** Script checks Python is installed (`Get-Command python`) before running, with helpful error if missing.
- **D-03:** Telethon session stored in `.session/` subfolder at project root (not a symlink or data/ folder).
- **D-04:** Script auto-installs pip dependencies on every run (`pip install -r requirements.txt`). Fast due to pip caching.

### Python Environment
- **D-05:** Use a Python virtual environment (`.venv/` in project root) for dependency isolation.
- **D-06:** Script auto-creates the venv if `.venv/Scripts/python.exe` doesn't exist (`python -m venv .venv`).
- **D-07:** Script checks Python version matches 3.14 (the project target version).
- **D-08:** Script adds `.venv/` to `.gitignore` if not already present.

### Entrypoint Equivalent
- **D-09:** Script does NOT replicate entrypoint.sh validation — relies on `config.py`'s built-in `ConfigError` for missing/invalid env vars.
- **D-10:** Script does NOT create `logs/` or `.session/` directories — Python creates them at runtime (`logging_setup.py mkdir(exist_ok=True)`, Telethon auto-creates session files).

### Session Storage
- **D-11:** Telegram session file lives in `.session/` at project root (not data/session/).
- **D-12:** `.session/` added to `.gitignore` to prevent committing auth tokens.

### Delivery Format
- **D-13:** Single `run.ps1` script — fully automated end-to-end.
- **D-14:** `run.ps1 --help` shows usage information.
- **D-15:** `run.ps1 --setup` runs venv/dependency setup without starting the pipeline.

### the agent's Discretion
- Exact PowerShell implementation details (parameter names, error messages, output formatting)
- Whether to use `python` or `py` launcher on Windows
- Specific PowerShell cmdlets for directory/file checks

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### System Architecture
- `AI-SPEC.md` — Full architecture, data flow, module responsibilities. Understanding the pipeline structure is essential.

### Existing Pipeline Code
- `src/config.py` — Config loading logic, REQUIRED_KEYS (8 env vars). Validates env vars on startup.
- `src/main.py` — Entry point (`python -m src.main`), asyncio event loop, signal handlers.
- `src/logging_setup.py` — `RotatingFileHandler` config. Logs auto-create `logs/` directory.
- `requirements.txt` — 5 Python dependencies (telethon, pydantic, python-dotenv, httpx, python-telegram-bot).
- `.env.example` — Template for all 8 required environment variables.

### Prior Phase Contracts
- `.planning/phases/06-deployment-ci-cd/06-CONTEXT.md` — D-03 (entrypoint.sh validation pattern), D-05 (volume mounts for .env, sources.json, logs/, session/). Context for what the Windows setup replaces.
- `.planning/phases/05-resilience-logging-monitoring/05-CONTEXT.md` — Logging patterns, directory auto-creation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `requirements.txt` — Directly usable via `pip install -r requirements.txt` inside the .ps1 script.
- `.env.example` — Template for .env creation. Script should check .env exists and reference this.
- `src/main.py` — `python -m src.main` invocation works identically on Windows.

### Established Patterns
- All config via `.env` + `sources.json` — same files used in Docker and local Windows.
- Entry point is `python -m src.main` — no change needed for Windows.
- Logging to `logs/` directory auto-created by `logging_setup.py` — no pre-creation needed.
- Long-running asyncio daemon — runs in PowerShell terminal, Ctrl+C for graceful shutdown.

### Integration Points
- Project root — `run.ps1` goes here alongside `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`.
- `.gitignore` — Needs `.session/` and `.venv/` entries (added by script).
- Local `.env` and `sources.json` — Same files used by Docker, now also used by local Windows run.

</code_context>

<specifics>
## Specific Ideas

- The .ps1 should mirror the Docker entrypoint's spirit (validate → init → run) but adapted for Windows idioms (PowerShell cmdlets instead of bash, config.py validation instead of grep).
- Session files in `.session/` folder — not symlinked like the Docker entrypoint's `ln -sf /app/session/telegram.session /app/telegram.session`.
- The script should be runnable from any terminal (PowerShell 5.1+, Windows 10/11).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-local-windows-dev-setup*
*Context gathered: 2026-05-23*
