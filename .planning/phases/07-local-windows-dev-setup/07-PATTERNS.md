# Phase 7: Local Windows Development Setup — Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 1 new (run.ps1)
**Analogs found:** 3 exact / 3 total

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `run.ps1` | script/entrypoint | request-response (validate → init → run) | `entrypoint.sh` | exact (role + data flow) |
| `.gitignore` (modify) | config | static | `.gitignore` (existing) | exact (same file) |

---

## Pattern Assignments

### `run.ps1` (script/entrypoint, request-response)

**Analog:** `entrypoint.sh` (`C:\Users\daotu\Documents\Crypto-News-Pipeline\entrypoint.sh`, lines 1-24)

**Imports pattern — N/A** (shell scripts have no imports)
*PowerShell*: uses cmdlets natively (`Get-Command`, `Test-Path`, `Write-Output`, etc.)
*Bash analog*: `#!/bin/sh` (line 1) → PS1 equivalent is no explicit shebang; relies on PowerShell host.

**Core pattern: Validate → Init → Run** (entrypoint.sh lines 1-24)

The `entrypoint.sh` follows a strict three-phase lifecycle:

**Phase 1 — Validate** (lines 5-16):
```bash
#!/bin/sh
set -e

echo "=== Crypto News Pipeline Entrypoint ==="

for f in sources.json .env; do
    if [ ! -f "$f" ]; then
        echo "ERROR: $f not found. Mount as a volume."
        exit 1
    fi
done

if grep -q "your_" .env 2>/dev/null; then
    echo "ERROR: .env contains placeholder values. Replace with real credentials."
    exit 1
fi
```

*PowerShell mapping (per D-09: rely on config.py, don't replicate validation):*
```powershell
# Validate: Check Python exists (D-02)
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { ... exit 1 }
# Validate: Check Python version matches 3.14 (D-07)
# Validate: Check .env exists (loose — config.py raises ConfigError)
# NO grep for placeholders — config.py _warn_defaults handles this
# NO directory creation — logging_setup.py & Telethon handle this (D-10)
```

**Phase 2 — Init** (lines 18-22):
```bash
mkdir -p logs
mkdir -p session

ln -sf /app/session/telegram.session /app/telegram.session
```

*PowerShell mapping (streamlined per D-10, D-11):*
```powershell
# Init: Ensure .venv exists (D-05, D-06)
if (-not (Test-Path ".venv/Scripts/python.exe")) { python -m venv .venv }
# Init: Install dependencies (D-04)
pip install -r requirements.txt
# NO mkdir for logs/ or .session/ — Python handles at runtime
# NO symlink — Telethon .session/ folder stored directly (D-03, D-11)
```

**Phase 3 — Run** (lines 23-24):
```bash
echo "Entrypoint validation passed. Starting pipeline..."
exec python -m src.main
```

*PowerShell mapping:*
```powershell
Write-Output "Setup complete. Starting pipeline..."
& ".venv/Scripts/python.exe" -m src.main
# NOTE: No exec equivalent in PowerShell — script runs in-process
# Ctrl+C sends SIGINT to Python process for graceful shutdown
```

**Entrypoint Exit/Error Handling** (entrypoint.sh lines 7-16):
```bash
# Fail-fast on missing files
if [ ! -f "$f" ]; then
    echo "ERROR: $f not found. Mount as a volume."
    exit 1
fi

# Fail-fast on placeholder values
if grep -q "your_" .env 2>/dev/null; then
    echo "ERROR: .env contains placeholder values. Replace with real credentials."
    exit 1
fi
```

*PowerShell mapping (rely on config.py per D-09):*
```powershell
# Use $ErrorActionPreference = 'Stop' for fail-fast
# No grep — config.py _warn_defaults() logs warning, doesn't block
# No file existence check — config.py load_config() raises ConfigError with clear message
```

**Key pattern difference — `exec` replacement** (entrypoint.sh line 24):
```bash
exec python -m src.main   # Replaces shell process; SIGTERM reaches Python directly
```

*PowerShell: no direct `exec` equivalent. Script should just invoke Python and wait:*
```powershell
& ".venv/Scripts/python.exe" -m src.main   # Ctrl+C works natively
```

**Entrypoint parameter flags** — not present in entrypoint.sh (Docker ENTRYPOINT has no CLI flags).
*run.ps1 adds D-13/D-14/D-15 flags:*
```powershell
param(
    [switch]$Help,
    [switch]$Setup
)
# --help: display usage info
# --setup: run venv + pip install, then exit (don't start pipeline)
```

---

### `.gitignore` (config, static — modify existing)

**Analog:** `C:\Users\daotu\Documents\Crypto-News-Pipeline\.gitignore` (lines 126-133, 195-198)

**Existing venv pattern** (lines 127-132):
```
# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/
```

**Note:** `.venv` (without trailing slash) on line 128 already matches `.venv\` directory on Windows. No change needed for venv — D-08 says "add if not already present," and it is.

**Existing project-specific patterns** (lines 195-198):
```
# Project-specific
telegram.session
sources.json
logs/
```

**New entry needed** (per D-12):
```
.session/
```

This is analogous to how `logs/` (line 198) is already gitignored — a runtime data directory that must not be committed.

---

## Shared Patterns

### Plan Document Template Format

**Source:** `.planning/phases/06-deployment-ci-cd/06-01-PLAN.md`
**Apply to:** `run.ps1` creation plan

The canonical plan template has these sections in order:

```
---
YAML front matter: phase, plan, type, wave, depends_on, files_modified, autonomous, requirements
must_haves:
  truths: [list of verifiable statements, each prefixed with (D-NN) when tied to a CONTEXT.md decision]
  artifacts: [list of path, provides, min_lines, contains]
  key_links: [list of from→to connections with via and pattern strings]
---

<objective>
One-paragraph goal + one-sentence purpose + "Output: file1, file2" list.
</objective>

<execution_context>
@ workflow/execute-plan.md path
@ templates/summary.md path
</execution_context>

<context>
@ 07-CONTEXT.md
@ 07-RESEARCH.md
@ [source files the plan reads]
</context>

<tasks>
  <task type="auto|manual" tdd="true|false">
    <name>Task N: description</name>
    <files>file1, file2</files>
    <read_first>-- Comment --</read_first>
    <acceptance_criteria>bullet list</acceptance_criteria>
    <action>implementation instructions</action>
    <verify><automated>shell commands to verify</automated></verify>
    <done>closure statement</done>
  </task>
</tasks>

<threat_model>
  Trust Boundaries table + STRIDE Threat Register table
</threat_model>

<verification>
1. Numbered checklist
</verification>

<success_criteria>
- Bullet list of what "done" looks like
</success_criteria>
```

**Key template patterns observed:**
1. **Decision annotations** — Truths in `must_haves` use `(D-NN)` prefixes to trace back to CONTEXT.md decisions
2. **`<context>` references** — Relative paths like `@.planning/phases/07-local-windows-dev-setup/07-CONTEXT.md` for context, absolute `@C:/...` for workflows
3. **Key links** — Documents cross-file relationships with `from→to→via→pattern` quadruple
4. **Task structure** — Each task has `type`, optional `tdd`, `files`, `read_first`, `acceptance_criteria`, `action`, `verify`, `done`
5. **Verification commands** — Inline shell commands in `<verify><automated>` blocks
6. **threat_model** — Always present with Trust Boundaries table + STRIDE table
7. **Single-file-per-task** — Simple files get one task; complex files get one task per file

### Validate → Init → Run Lifecycle

**Source:** `entrypoint.sh` (lines 1-24)
**Apply to:** `run.ps1`

| Phase | entrypoint.sh (bash) | run.ps1 (PowerShell) |
|---|---|---|
| **Validate** | Check `.env` `sources.json` exist; grep "your_" placeholders; `set -e` | Check Python installed + version; let `config.py` validate env vars |
| **Init** | `mkdir -p logs session`; `ln -sf` for session | `python -m venv .venv` if missing; `pip install -r requirements.txt` |
| **Run** | `exec python -m src.main` (replaces shell) | `& ".venv/Scripts/python.exe" -m src.main` (no exec equivalent) |

**Decision trace:**
- D-01: PS1 format (not .bat, not bash)
- D-02: Check Python is installed
- D-03: Session in `.session/` (not symlinked)
- D-04: Auto-install deps every run
- D-05: Use `.venv/` for isolation
- D-06: Auto-create venv if missing
- D-07: Check Python 3.14
- D-08: Add `.venv/` to `.gitignore` (already present)
- D-09: Rely on `config.py` validation (not grep)
- D-10: Dirs auto-created by Python (not script)
- D-11: `.session/` at project root
- D-12: `.session/` in `.gitignore`
- D-13: Single `run.ps1`
- D-14: `--help` flag
- D-15: `--setup` flag

### How Prior Plans Reference Files and Contexts

**Source:** `06-01-PLAN.md` (lines 58-71), `05-01-PLAN.md` (lines 53-65)

Three distinct reference styles used:

1. **Execution context** (absolute paths — OpenCode workflow templates):
   ```markdown
   <execution_context>
   @C:/Users/daotu/Documents/Crypto-News-Pipeline/.opencode/get-shit-done/workflows/execute-plan.md
   @C:/Users/daotu/Documents/Crypto-News-Pipeline/.opencode/get-shit-done/templates/summary.md
   </execution_context>
   ```

2. **Context references** (relative paths — phase docs + research):
   ```markdown
   <context>
   @.planning/phases/07-local-windows-dev-setup/07-CONTEXT.md
   @.planning/phases/07-local-windows-dev-setup/07-RESEARCH.md
   @requirements.txt
   @src/main.py
   @src/config.py
   @.gitignore
   </context>
   ```

3. **Task-specific read_first** (relative paths — source code to study for implementation):
   ```markdown
   <read_first>
   -- Source of truth for entrypoint behavior --
   .planning/phases/07-local-windows-dev-setup/07-CONTEXT.md  (D-03: entrypoint script...)
   .planning/phases/07-local-windows-dev-setup/07-RESEARCH.md  (Pattern 1: ...)
   src/config.py  (REQUIRED_KEYS list...)
   src/main.py  (entry point: ...)
   </read_first>
   ```

**Cross-phase references** (`06-CONTEXT.md` lines 65-70):
```markdown
### Prior Phase Contracts
- `.planning/phases/05-resilience-logging-monitoring/05-CONTEXT.md` — D-11 (logging...)
- `.planning/phases/04-publisher/04-CONTEXT.md` — Publishing patterns...
```

### File Interaction Map for run.ps1

| File | Interaction | Pattern |
|---|---|---|
| `.venv/Scripts/python.exe` | Existence check → `python -m venv .venv` if missing (D-06) | Read + Create |
| `requirements.txt` | `pip install -r requirements.txt` (D-04) | Read-only |
| `.env` | Must exist (config.py validates content) | Read-only |
| `sources.json` | Must exist (config.py validates content) | Read-only |
| `.gitignore` | Ensure `.venv/` and `.session/` are ignored (D-08, D-12) | Modify |
| `src/main.py` | Invocation target: `python -m src.main` | Execute |
| `.session/` | Telethon session storage (D-03, D-11) | Create (auto) |
| `logs/` | Log file output (auto-created by `logging_setup.py`) | Create (auto) |

### .gitignore Modifications Needed

**Current state** (lines 126-133, 195-198):
```
# Environments           ← section header
.env
.venv                    ← matches .venv\ on Windows (no trailing / needed)
env/
venv/
ENV/
...
# Project-specific       ← section header
telegram.session
sources.json
logs/
```

**Required change** — add `.session/` under Project-specific section:
```
# Project-specific
telegram.session
sources.json
logs/
.session/                ← NEW (D-12)
```

**Note:** `.venv` (line 128) already matches `.venv\` directory. D-08 condition ("add if not present") is satisfied — no change needed for venv.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| None | — | — | All files have close analogs |

The `run.ps1` has a direct structural analog in `entrypoint.sh` (same validate → init → run lifecycle). The `.gitignore` modification follows existing gitignore patterns. No novel file types are being introduced.

---

## Metadata

**Analog search scope:** `C:\Users\daotu\Documents\Crypto-News-Pipeline\`
- `entrypoint.sh` — primary analog (role + data flow exact match)
- `.gitignore` — secondary analog (same file, modification)
- `06-01-PLAN.md` — template structure analog
- `05-01-PLAN.md` — alternate template structure analog
- `src/config.py` — validation pattern that run.ps1 relies on (D-09)
- `src/logging_setup.py` — directory auto-creation pattern (D-10)
- `src/main.py` — invocation target

**Files scanned:** 12
**Pattern extraction date:** 2026-05-24
