---
phase: 07-local-windows-dev-setup
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - run.ps1
  - .gitignore
autonomous: true
requirements: []
must_haves:
  truths:
    - (D-01) "User can run .\run.ps1 from PowerShell and the pipeline starts"
    - (D-02) "Script errors with clear message if Python is not installed"
    - (D-07) "Script errors with clear message if Python version is not 3.14"
    - (D-05, D-06) "Virtual environment is auto-created at .venv/ if missing"
    - (D-04) "Dependencies are auto-installed from requirements.txt on every run"
    - (D-14) "User can run .\run.ps1 --help and see usage information"
    - (D-15) "User can run .\run.ps1 --setup and only setup runs (no pipeline start)"
    - (D-12) ".session/ is listed in .gitignore — auth tokens never committed"
    - (D-09) "Missing/invalid env vars produce config.py ConfigError — not replicated script validation"
    - (D-10) "logs/ and .session/ are NOT pre-created by the script — Python creates at runtime"
  artifacts:
    - path: "run.ps1"
      provides: "Single PowerShell script for local Windows development — validate, init, run lifecycle"
      min_lines: 80
      contains: "param("
    - path: ".gitignore"
      provides: "Excludes .session/ from version control"
      min_lines: 200
      contains: ".session/"
  key_links:
    - from: "run.ps1"
      to: ".venv/Scripts/python.exe"
      via: "virtual environment activation"
      pattern: ".venv.*Scripts.*python"
    - from: "run.ps1"
      to: "requirements.txt"
      via: "pip install -r requirements.txt (D-04)"
      pattern: "pip install"
    - from: "run.ps1"
      to: "src/main.py"
      via: "python -m src.main (D-13)"
      pattern: "src.main"
    - from: "run.ps1"
      to: ".gitignore"
      via: "ensure .venv/ and .session/ are ignored (D-08, D-12)"
      pattern: "Add-Content.*gitignore"
    - from: "run.ps1"
      to: "src/config.py"
      via: "delegated validation (D-09) — no env var grep in script"
      pattern: "python -m src.main"
---

<objective>
Create a single PowerShell script (`run.ps1`) that enables running the crypto-news-pipeline natively on Windows without Docker. The script automates Python environment validation, virtual environment setup, dependency installation, and pipeline execution — providing a fast local dev loop on Windows.

Purpose: Replace Docker/container dependency for local development on Windows with a streamlined PS1 script that mirrors the entrypoint.sh validate→init→run lifecycle but adapted for Windows idioms (PowerShell cmdlets, config.py delegation, no symlinks).

Output: `run.ps1` (new), `.gitignore` (modified — add `.session/` entry).
</objective>

<execution_context>
@C:/Users/daotu/Documents/Crypto-News-Pipeline/.opencode/get-shit-done/workflows/execute-plan.md
@C:/Users/daotu/Documents/Crypto-News-Pipeline/.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-local-windows-dev-setup/07-CONTEXT.md
@.planning/phases/07-local-windows-dev-setup/07-PATTERNS.md
@entrypoint.sh
@.gitignore
@src/main.py
@src/config.py
@src/logging_setup.py
@requirements.txt
@.env.example
@Dockerfile
</context>

<tasks>

<!-- ============================================================ -->
<!-- WAVE 1 — CREATE CORE run.ps1 SCRIPT                          -->
<!-- ============================================================ -->
<task type="auto">
  <name>Task 1 (Wave 1): Create run.ps1 — full Validate → Init → Run PowerShell script</name>
  <files>run.ps1</files>
  <read_first>
    -- Source of truth for script behavior and all 15 decisions --
    .planning/phases/07-local-windows-dev-setup/07-CONTEXT.md  (D-01 through D-15 — all decisions)
    .planning/phases/07-local-windows-dev-setup/07-PATTERNS.md  (Validate→Init→Run lifecycle mapping, entrypoint.sh analog)
    entrypoint.sh  (structural analog — lines 1-24: validate→init→run)
    src/config.py  (REQUIRED_KEYS list lines 13-22; ConfigError validation lines 62-79; _warn_defaults lines 53-59)
    src/main.py  (entry point: `python -m src.main` — lines 139-140)
    src/logging_setup.py  (log_dir.mkdir(exist_ok=True) — lines 38-39: D-10 evidence)
    requirements.txt  (5 packages to install)
    .env.example  (template for env vars — script references this in --help)
  </read_first>
  <acceptance_criteria>
    - (D-01) File is `run.ps1` — PowerShell script format
    - (D-02) Uses `Get-Command python -ErrorAction SilentlyContinue` to check Python is installed; exits 1 with help message if missing
    - (D-07) Runs `python --version`, parses output, exits 1 if not Python 3.14.x
    - (D-05, D-06) Checks `.venv/Scripts/python.exe` existence via `Test-Path`; runs `python -m venv .venv` if missing
    - (D-04) Runs `& ".venv/Scripts/python.exe" -m pip install -r requirements.txt` unconditionally (pip cache makes it fast)
    - (D-08) Reads `.gitignore` content; adds `.venv/` line if not already present via `Add-Content`
    - (D-12) Reads `.gitignore` content; adds `.session/` line if not already present via `Add-Content`
    - (D-09) Does NOT grep/replicate entrypoint.sh validation for .env/sources.json — relies on config.py ConfigError
    - (D-10) Does NOT call `mkdir` or `New-Item` for logs/ or .session/ directories — Python creates at runtime
    - (D-03, D-11) No symlink logic — session directory is `.session/` directly (not symlinked)
    - (D-13) Single `run.ps1` file — no companion scripts, no .bat wrappers
    - (D-14) `param([switch]$Help)` block at top; `--help` displays usage via `Write-Output` and exits 0
    - (D-15) `param([switch]$Setup)` block at top; `--setup` runs venv + pip install then exits 0 without starting pipeline
    - (D-13) Default (no flags): runs full validate→init→run sequence, ends with `& ".venv/Scripts/python.exe" -m src.main`
    - Uses `$ErrorActionPreference = 'Stop'` for fail-fast behavior
    - Uses `Split-Path -Parent $MyInvocation.MyCommand.Path` to derive project root (works from any working directory)
    - Writes progress messages via `Write-Output` for each lifecycle phase
    - Comments reference the D-NN decision ID for each major block for traceability
    - No fenced code blocks in the script (pure PowerShell syntax)
  </acceptance_criteria>
  <action>
    Create `run.ps1` at project root. Structure the script as follows:

    **Header + Parameters (lines 1-20):**
    - `<# .SYNOPSIS #>` comment block at top with script name and description
    - `param(` block with two `[switch]` parameters: `$Help` and `$Setup`
    - Set `$ErrorActionPreference = 'Stop'` for fail-fast semantics
    - Derive `$ProjectRoot` via `Split-Path -Parent $MyInvocation.MyCommand.Path`
    - Define derived paths: `$VenvPath = Join-Path $ProjectRoot ".venv"`, `$PythonExe = Join-Path $VenvPath "Scripts" "python.exe"`, `$Requirements = Join-Path $ProjectRoot "requirements.txt"`, `$GitIgnore = Join-Path $ProjectRoot ".gitignore"`
    - Set-Location to $ProjectRoot so all relative Python paths resolve correctly

    **--help handler (lines ~22-30):**
    - `if ($Help) { ... exit 0 }`
    - Display: "Crypto News Pipeline — Windows Development Script" as title
    - Display: "Usage: .\run.ps1 [--help] [--setup]" with description
    - Display option descriptions: --help shows this, --setup runs setup without pipeline, default runs full pipeline
    - Include hint: "Copy .env.example to .env and fill in credentials before starting"
    - Per D-14

    **Validation Phase (lines ~32-55):**
    - Print "=== Crypto News Pipeline — Windows Setup ===" banner
    - Print "[Validate] Checking prerequisites..."
    - (D-02) Check Python installed: `if (-not (Get-Command python -ErrorAction SilentlyContinue))` → Write-Error "Python is not installed. Install Python 3.14 from https://www.python.org/downloads/" and exit 1. Use Write-Error (red text in PowerShell) then exit 1 separately (Write-Error does not halt execution with 'Stop' preference on its own).
    - (D-07) Check Python version: capture `python --version` output via `& python --version 2>&1`. Parse with `-match` regex `"3\.14"` (e.g. `$PythonVersion = & python --version 2>&1; if ($PythonVersion -notmatch "3\.14") { Write-Error "Python 3.14 required. Detected: $($PythonVersion.Trim())"; exit 1 }`)
    - (D-09) Do NOT check .env existence or content — config.py raises ConfigError with clear message if missing (see src/config.py lines 104-108: `raise ConfigError(".env file not found...")`). Do NOT check sources.json. Do NOT grep for "your_" placeholders.
    - (D-10) Do NOT create logs/ or .session/ directories. logging_setup.py line 39 calls `log_dir.mkdir(exist_ok=True)`. Telethon auto-creates session file at runtime.

    **Init Phase (lines ~57-85):**
    - Print "[Init] Setting up environment..."
    - (D-05, D-06) Check venv: `if (-not (Test-Path $PythonExe)) { Write-Output "Creating virtual environment..."; & python -m venv $VenvPath; if (-not $?) { Write-Error "Failed to create virtual environment"; exit 1 } }`
    - (D-04) Install deps: `Write-Output "Installing dependencies..."; & $PythonExe -m pip install -r $Requirements`. Use `-m pip` to ensure pip runs from the venv's Python. Do NOT add `--quiet` flag (user should see progress).
    - (D-08) Ensure .venv/ in .gitignore: Read `$GitIgnore` content with `Get-Content -Raw`. Use regex `(?m)^\.venv/?$` to check. If absent, `Add-Content $GitIgnore "`n.venv/"`. Print message if added. NOTE: `.venv` line 128 already exists in current .gitignore (matches `.venv\` on Windows), so this will be a no-op unless the line is removed for some reason — implement the check defensively per D-08.
    - (D-12) Ensure .session/ in .gitignore: Same pattern with regex `(?m)^\.session/?$`. Add `Add-Content $GitIgnore "`n.session/"` if missing. Print message if added.

    **--setup flag early exit (lines ~87-92):**
    - `if ($Setup) { Write-Output "Setup complete. Run .\run.ps1 to start the pipeline."; exit 0 }`
    - Per D-15

    **Run Phase (lines ~94-100):**
    - Print "[Run] Starting pipeline..."
    - (D-03, D-11) No symlink — Telethon in .session/ is handled by runtime. No special directory creation.
    - (D-09) Validation fully delegated — env vars and sources.json are validated by config.py when python -m src.main runs
    - (D-10) No pre-creation of directories
    - Execute: `& $PythonExe -m src.main`
    - NOTE: PowerShell has no `exec` equivalent. The script invokes Python in-process. Ctrl+C in PowerShell sends SIGINT to Python for graceful shutdown (src/main.py lines 119-125 handle signal handlers with try/except NotImplementedError for Windows).

    **Error handling pattern throughout:**
    - Use `if (-not $?) { Write-Error "..."; exit 1 }` after each critical operation (venv creation, pip install)
    - After each check that calls exit, the script terminates — no fallthrough

    **Comment each major section with the decision IDs:**
    - `# D-02: Check Python is installed`
    - `# D-07: Check Python version 3.14`
    - `# D-05, D-06: Auto-create venv if missing`
    - `# D-04: Auto-install dependencies`
    - `# D-08: Ensure .venv/ in .gitignore`
    - `# D-12: Ensure .session/ in .gitignore`
    - `# D-09: Validation delegated to config.py`
    - `# D-10: Directories created by Python at runtime`
    - `# D-03, D-11: Session in .session/ — no symlink`

    **PowerShell-specific patterns to use:**
    - Use `Get-Command` for existence checks (not `where.exe`)
    - Use `Test-Path` for file/directory checks (not `-not (Get-ChildItem ...)`)
    - Use `Write-Output` for informational messages, `Write-Error` for errors (red text)
    - Use `$MyInvocation.MyCommand.Path` to get script location (works from any terminal path)
    - Use `Join-Path` for path construction (not string concatenation)
    - Use `$()` for subexpressions in strings
    - Use backtick `` `n `` for newlines in strings
    - Use `-match` for regex matching (case-insensitive by default in PowerShell)
    - Use `exit 1` for error exits (returns non-zero exit code to shell)
    - Use `-not` for negation, not `!`
    - Use `param([switch]$Help, [switch]$Setup)` for flags — PowerShell auto-creates `--help` and `--setup` parameters from PascalCase switch names
    - Do NOT use Write-Host (Write-Output and Write-Error are the correct cmdlets)
    - Do NOT use `#requires` or module import statements (script uses only built-in cmdlets)
  </action>
  <verify>
    <automated>
      # File exists
      Test-Path "run.ps1"; if ($?) { Write-Output "PASS: run.ps1 exists" } else { Write-Output "FAIL: run.ps1 missing" }

      # Has param block with --help and --setup
      $Content = Get-Content "run.ps1" -Raw
      if ($Content -match '\$Help' -and $Content -match '\$Setup') { Write-Output "PASS: --help and --setup params defined" } else { Write-Output "FAIL: missing param switches" }

      # Has Get-Command python check (D-02)
      if ($Content -match 'Get-Command.*python') { Write-Output "PASS: Python installed check (D-02)" } else { Write-Output "FAIL: missing Get-Command python (D-02)" }

      # Has Python version check (D-07)
      if ($Content -match '3\.14') { Write-Output "PASS: Python version check (D-07)" } else { Write-Output "FAIL: missing version check (D-07)" }

      # Has venv auto-creation (D-05, D-06)
      if ($Content -match 'python.*-m venv') { Write-Output "PASS: venv auto-create (D-05, D-06)" } else { Write-Output "FAIL: missing venv creation (D-05, D-06)" }

      # Has pip install (D-04)
      if ($Content -match 'pip install') { Write-Output "PASS: pip install (D-04)" } else { Write-Output "FAIL: missing pip install (D-04)" }

      # Has .gitignore modification for .venv (D-08) and .session (D-12)
      if ($Content -match '\.gitignore') { Write-Output "PASS: .gitignore modification (D-08, D-12)" } else { Write-Output "FAIL: missing .gitignore logic" }

      # Has python -m src.main (D-13)
      if ($Content -match 'src\.main') { Write-Output "PASS: pipeline start command (D-13)" } else { Write-Output "FAIL: missing src.main invocation" }

      # Does NOT have mkdir for logs/ or .session/ (D-10)
      if ($Content -notmatch 'mkdir.*logs' -and $Content -notmatch 'New-Item.*logs' -and $Content -notmatch 'mkdir.*\.session' -and $Content -notmatch 'New-Item.*\.session') { Write-Output "PASS: no dir pre-creation (D-10)" } else { Write-Output "FAIL: script pre-creates directories (D-10 violation)" }

      # Does NOT have grep-like validation (D-09)
      if ($Content -notmatch 'config\.py|grep|your_|sources\.json') { Write-Output "PASS: no duplicated validation (D-09)" } else { Write-Output "NOTE: config.py reference expected, grep/your_/sources.json checks would violate D-09" }
    </automated>
  </verify>
  <done>
    run.ps1 created at project root with: --help flag showing usage (D-14), --setup flag for setup-only mode (D-15), Python installed check via Get-Command (D-02), Python 3.14 version check (D-07), auto-venv creation at .venv/ (D-05, D-06), unconditional pip install from requirements.txt (D-04), .gitignore safeguarding for .venv/ and .session/ (D-08, D-12), no duplicated entrypoint validation (D-09), no directory pre-creation (D-10), no symlink logic (D-03, D-11), default run invokes python -m src.main (D-13)
  </done>
</task>

<!-- ============================================================ -->
<!-- WAVE 2 — .GITIGNORE UPDATE & VERIFICATION                    -->
<!-- ============================================================ -->
<task type="auto">
  <name>Task 2 (Wave 2): Update .gitignore with .session/ entry</name>
  <files>.gitignore</files>
  <read_first>
    -- Current .gitignore, section to modify --
    .gitignore  (lines 195-198: # Project-specific section, add .session/ after logs/)
    .planning/phases/07-local-windows-dev-setup/07-PATTERNS.md  (lines 345-350: exact diff)
  </read_first>
  <acceptance_criteria>
    - (D-12) `.session/` line is present under the `# Project-specific` section
    - (D-08) `.venv` is already present in the `# Environments` section (line 128) — confirmed no change needed
    - File remains syntactically valid (no duplicate lines, no empty trailing sections)
    - Exactly one new line added: `.session/` under `# Project-specific` after `logs/`
  </acceptance_criteria>
  <action>
    Edit `.gitignore` to add `.session/` under the `# Project-specific` section after the `logs/` line.

    Current state of the Project-specific section (lines 195-198):
    ```
    # Project-specific
    telegram.session
    sources.json
    logs/
    ```

    Change to:
    ```
    # Project-specific
    telegram.session
    sources.json
    logs/
    .session/
    ```

    **Important notes:**
    - `.venv` (without trailing slash) at line 128 already matches `.venv\` directory on Windows Git — D-08 condition ("add if not already present") is already satisfied. No change needed for the venv entry.
    - `.session/` uses trailing slash (gitignore convention for directory matching), matching the existing pattern used by `logs/`, `env/`, `venv/`, etc.
    - Insert after the `logs/` line to keep the project-specific section ordered alphabetically within runtime data directories.
    - Do NOT modify any other section of the file.
    - Do NOT add blank lines or trailing whitespace.
    - Verify the change by reading the modified file's last lines.
  </action>
  <verify>
    <automated>
      # Check .session/ is in gitignore
      $GitContent = Get-Content ".gitignore" -Raw
      if ($GitContent -match '(?m)^\.session/') { Write-Output "PASS: .session/ in .gitignore (D-12)" } else { Write-Output "FAIL: .session/ not in .gitignore" }

      # Check .venv already present (D-08 satisfied)
      if ($GitContent -match '(?m)^\.venv') { Write-Output "PASS: .venv already in .gitignore (D-08 satisfied)" } else { Write-Output "FAIL: .venv not in .gitignore — script will add it" }

      # Verify it's under Project-specific section
      $Lines = Get-Content ".gitignore"
      $PSIndex = $Lines.IndexOf("# Project-specific")
      if ($PSIndex -ge 0) {
        $AfterSection = $Lines[($PSIndex+1)..($PSIndex+5)]
        if ($AfterSection -contains ".session/") { Write-Output "PASS: .session/ placed under # Project-specific section" } else { Write-Output "FAIL: .session/ not in Project-specific section" }
      }
    </automated>
  </verify>
  <done>
    .gitignore updated: `.session/` added under `# Project-specific` section after `logs/`. `.venv` confirmed already present at line 128 under `# Environments`.
  </done>
</task>

<task type="auto">
  <name>Task 3 (Wave 2): Validate script syntax and verify end-to-end testing instructions</name>
  <files>run.ps1</files>
  <read_first>
    -- Script to validate --
    run.ps1
  </read_first>
  <acceptance_criteria>
    - PowerShell syntax is valid (no parse errors when loaded in PowerShell 5.1+)
    - All 15 decisions (D-01 through D-15) are implemented by the script (verified by automated grep checks)
    - `.\run.ps1 -?` works (PowerShell built-in for param help)
    - `.\run.ps1 --help` displays usage and exits 0
    - Script paths use `Join-Path` (not hardcoded `\`) — works on any Windows system
    - No dependency on external PowerShell modules (only built-in cmdlets)
    - Testing steps are recorded in SUMMARY.md for the human to run manually
  </acceptance_criteria>
  <action>
    Perform comprehensive validation of run.ps1:

    1. **Syntax validation**: Run `$PSVersionTable.PSVersion` to verify PowerShell version, then use `[System.Management.Automation.Language.Parser]::ParseFile("run.ps1", [ref]$null, [ref]$null)` to check for parse errors. The parser returns null errors on success.

    2. **Decision coverage audit**: Run automated grep checks to confirm ALL 15 decisions are implemented. Use the verification commands from Task 1's `<verify>` block plus additional checks:
       - D-01: File is `.ps1` extension → `(Get-Item "run.ps1").Extension -eq '.ps1'`
       - D-02: `Get-Command python` → grep check
       - D-03: `.session/` referenced → grep check
       - D-04: `pip install` → grep check
       - D-05: `.venv` path constructed → grep check
       - D-06: `python -m venv` → grep check
       - D-07: `3.14` or version check → grep check
       - D-08: `.gitignore` + `.venv` → grep check
       - D-09: NO grep for `sources.json`, `.env` content, or `your_` → grep negative check
       - D-10: NO `mkdir`/`New-Item` for `logs` or `.session` → grep negative check
       - D-11: `.session/` at project root → grep check (same as D-03)
       - D-12: `.gitignore` + `.session` → grep check
       - D-13: Single file → no companion files detected
       - D-14: `$Help` switch → grep check
       - D-15: `$Setup` switch → grep check

    3. **Compile audit results**: Generate a table showing:
       ```
       | Decision | Implemented? | Evidence |
       |----------|-------------|----------|
       | D-01     | ✓            | run.ps1 extension |
       | D-02     | ✓            | Get-Command python check |
       | ...      | ...          | ... |
       ```

    4. **Record end-to-end manual testing steps** in a testing section in the SUMMARY.md:

       **Prerequisites for manual test:**
       - Windows 10/11 with PowerShell 5.1+
       - Python 3.14 installed (https://www.python.org/downloads/)
       - .env file with valid credentials (copy from .env.example)
       - sources.json file with valid sources

       **Manual test steps:**
       1. Open PowerShell in project root
       2. Run `.\run.ps1 --help` — verify usage text appears
       3. Run `.\run.ps1 --setup` — verify venv is created, deps install, no pipeline start
       4. (Optional) Run `.\run.ps1` — verify pipeline starts (requires valid credentials to fully run; otherwise config.py ConfigError is expected and acceptable)
       5. Verify `.session/` is in `.gitignore`
       6. Verify `.venv/` is in `.gitignore` (already present)
       7. Verify `logs/` directory and `.session/` directory are NOT created by --setup alone

    5. **If any grep check fails**: Log the failure in the decision coverage table with the missing pattern. Do NOT modify the script — report as a gap for the executor to fix.

    **Important**: Do NOT actually run `.\run.ps1` during Task 3 — syntax validation only. Actual execution requires user credentials in .env. If syntax validation fails, report the parse error for the executor to fix.
  </action>
  <verify>
    <automated>
      # PowerShell syntax check
      $Errors = $null; $Tokens = $null
      [System.Management.Automation.Language.Parser]::ParseFile("run.ps1", [ref]$Tokens, [ref]$Errors)
      if ($Errors.Count -eq 0) { Write-Output "PASS: PowerShell syntax valid" } else { Write-Output "FAIL: Parse errors found"; $Errors | ForEach-Object { Write-Output "$($_.Extent.StartLineNumber): $($_.Message)" } }

      # Complete decision coverage audit
      $Content = Get-Content "run.ps1" -Raw
      $Results = @{}
      $Results["D-01"] = ((Get-Item "run.ps1").Extension -eq '.ps1')
      $Results["D-02"] = ($Content -match 'Get-Command.*python')
      $Results["D-03"] = ($Content -match '\.session')
      $Results["D-04"] = ($Content -match 'pip install')
      $Results["D-05"] = ($Content -match '\.venv')
      $Results["D-06"] = ($Content -match 'python.*-m venv')
      $Results["D-07"] = ($Content -match '3\.14')
      $Results["D-08"] = ($Content -match '\.venv' -and $Content -match '\.gitignore')
      $Results["D-09"] = ($Content -notmatch 'sources\.json|your_' -and $Content -notmatch "grep")
      $Results["D-10"] = ($Content -notmatch 'mkdir.*logs|New-Item.*logs|mkdir.*\.session|New-Item.*\.session')
      $Results["D-11"] = ($Content -match '\.session')
      $Results["D-12"] = ($Content -match '\.session' -and $Content -match '\.gitignore')
      $Results["D-13"] = ($Content -match 'src\.main')
      $Results["D-14"] = ($Content -match '\$Help')
      $Results["D-15"] = ($Content -match '\$Setup')

      Write-Output "`nDecision Coverage Audit:"
      $AllPassed = $true
      $Results.Keys | Sort-Object | ForEach-Object {
        $Status = if ($Results[$_]) { "✓" } else { "✗"; $AllPassed = $false }
        Write-Output "$Status $_"
      }
      if ($AllPassed) { Write-Output "`nPASS: All 15 decisions implemented" } else { Write-Output "`nFAIL: Some decisions not detected — review script" }
    </automated>
  </verify>
  <done>
    run.ps1 passes PowerShell syntax validation. All 15 decisions (D-01 through D-15) confirmed implemented by automated coverage audit. Manual testing steps recorded for human execution.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User's terminal → run.ps1 | User invokes script from PowerShell; script reads/writes project files |
| run.ps1 → Python venv | Script invokes `python -m venv .venv` to bootstrap isolated environment |
| run.ps1 → pip install | Script installs external packages from PyPI (telethon, pydantic, dotenv, httpx, python-telegram-bot) |
| run.ps1 → .gitignore | Script modifies .gitignore to add .session/ and .venv/ ignore rules |
| Python process → Telethon API | Pipeline uses Telegram API credentials stored in .env |
| Python process → OpenRouter/Binance API | Pipeline uses additional API keys from .env |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07-01 | Tampering | pip install (requirements.txt) | mitigate | Install from version-pinned requirements.txt. No `--user` flag — installs into isolated .venv only. |
| T-07-02 | Information Disclosure | Session files (.session/) | mitigate | `.session/` added to .gitignore (D-12) — auth tokens never committed. Users must manually exclude from any backups. |
| T-07-03 | Information Disclosure | Virtual environment (.venv/) | accept | `.venv/` in .gitignore prevents accidental commit. No secrets stored in venv by default. Low-value target. |
| T-07-04 | Spoofing | run.ps1 itself | mitigate | Script lives in project root under version control. Any tampering shows in `git diff`. User should verify before running. |
| T-07-05 | Elevation of Privilege | Python process startup | mitigate | Script runs with user's permissions only. No admin elevation requested. Pipeline is network-only (no local privesc surface). |
| T-07-SC | Tampering | NuGet/PyPI packages | mitigate | All 5 packages from requirements.txt are well-known: telethon, pydantic, python-dotenv, httpx, python-telegram-bot. Slopcheck: [ASSUMED] — established packages from prior phases. Install checkpoint not required. |
</threat_model>

<verification>
1. `run.ps1` exists at project root — single file (D-13)
2. PowerShell syntax: `[System.Management.Automation.Language.Parser]::ParseFile("run.ps1", [ref]$null, [ref]$null)` returns zero errors
3. All 15 decisions (D-01 through D-15) pass automated grep coverage audit
4. `.gitignore` contains `.session/` under `# Project-specific` section (D-12)
5. `.venv` confirmed already in `.gitignore` under `# Environments` (D-08 satisfied)
6. `.\run.ps1 --help` exits 0 with usage text (human verify)
7. `.\run.ps1 --setup` creates .venv, installs deps, does NOT start pipeline (human verify)
8. No `mkdir`/`New-Item` calls for logs/ or .session/ in script (grep negative check — D-10)
9. No `grep`/`your_`/`sources.json` validation in script (grep negative check — D-09)
</verification>

<success_criteria>
- [ ] `run.ps1` exists with all 15 decisions implemented (verified by automated coverage audit)
- [ ] `.gitignore` has `.session/` entry under `# Project-specific` section
- [ ] `.\run.ps1 --help` displays usage information and exits (D-14)
- [ ] `.\run.ps1 --setup` creates `.venv/` and installs requirements without starting pipeline (D-15)
- [ ] `.\run.ps1` (no flags) runs: Python check → venv auto-create → pip install → python -m src.main (D-13)
- [ ] Missing Python exits with helpful message pointing to python.org (D-02)
- [ ] Wrong Python version (not 3.14) exits with version mismatch message (D-07)
- [ ] Invalid/missing .env produces config.py ConfigError — not script-level grep validation (D-09)
- [ ] logs/ and .session/ are NOT pre-created by run.ps1 — Python creates them at runtime (D-10)
</success_criteria>

<output>
Create `.planning/phases/07-local-windows-dev-setup/01-01-SUMMARY.md` when done
</output>
