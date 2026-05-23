<#
.SYNOPSIS
    Crypto News Pipeline — Windows Development Script
    Runs the crypto-news-pipeline natively on Windows without Docker.
.DESCRIPTION
    Automates Python environment setup, dependency installation, and pipeline
    execution. Replaces the Docker entrypoint.sh for local Windows development.
.PARAMETER Help
    Display usage information and exit.
.PARAMETER Setup
    Run virtual environment setup and dependency installation only.
    Does NOT start the pipeline.
.EXAMPLE
    .\run.ps1 --help
    Shows usage information.
.EXAMPLE
    .\run.ps1 --setup
    Creates .venv and installs dependencies, then exits.
.EXAMPLE
    .\run.ps1
    Validates Python, sets up environment, and starts the pipeline.
#>
param(
    [switch]$Help,
    [switch]$Setup
)

$ErrorActionPreference = 'Stop'

# D-01: Derive project root from script location
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts" "python.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$GitIgnore = Join-Path $ProjectRoot ".gitignore"
$SessionDir = Join-Path $ProjectRoot ".session"

Set-Location -LiteralPath $ProjectRoot

# D-14: --help flag
if ($Help) {
    Write-Output "Crypto News Pipeline — Windows Development Script"
    Write-Output ""
    Write-Output "Usage: .\run.ps1 [--help] [--setup]"
    Write-Output ""
    Write-Output "Options:"
    Write-Output "  --help     Show this usage information"
    Write-Output "  --setup    Create .venv and install dependencies, then exit"
    Write-Output ""
    Write-Output "Default (no flags):"
    Write-Output "  Validate Python -> create .venv if missing -> install deps -> start pipeline"
    Write-Output ""
    Write-Output "Prerequisites:"
    Write-Output "  - Python 3.14 installed"
    Write-Output "  - .env file with credentials (copy from .env.example)"
    Write-Output "  - sources.json with valid sources"
    exit 0
}

Write-Output "=== Crypto News Pipeline — Windows Setup ==="
Write-Output "[Validate] Checking prerequisites..."

# D-02: Check Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed. Install Python 3.14 from https://www.python.org/downloads/"
    exit 1
}

# D-07: Check Python version is 3.14
$PythonVersion = & python --version 2>&1
if ($PythonVersion -notmatch "3\.14") {
    Write-Error "Python 3.14 required. Detected: $($PythonVersion.Trim())"
    exit 1
}

# D-09: Validation delegated to config.py — no grep checks for .env or sources.json
# D-10: Directories created by Python at runtime — no mkdir/New-Item for logs/ or .session/

Write-Output "[Init] Setting up environment..."

# D-05, D-06: Auto-create venv if missing
if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Output "Creating virtual environment..."
    & python -m venv $VenvPath
    if (-not $?) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
}

# D-04: Auto-install dependencies on every run
Write-Output "Installing dependencies..."
& $PythonExe -m pip install -r $Requirements
if (-not $?) {
    Write-Error "Failed to install dependencies"
    exit 1
}

# D-08: Ensure .venv/ in .gitignore (defensive check — already present at line 128)
if (Test-Path -LiteralPath $GitIgnore) {
    $GitContent = Get-Content -LiteralPath $GitIgnore -Raw
    if ($GitContent -notmatch '(?m)^\.venv/?$') {
        Add-Content -LiteralPath $GitIgnore -Value "`n.venv/"
        Write-Output "Added .venv/ to .gitignore"
    }
}

# D-12: Ensure .session/ in .gitignore
if (Test-Path -LiteralPath $GitIgnore) {
    $GitContent = Get-Content -LiteralPath $GitIgnore -Raw
    if ($GitContent -notmatch '(?m)^\.session/?$') {
        Add-Content -LiteralPath $GitIgnore -Value "`n.session/"
        Write-Output "Added .session/ to .gitignore"
    }
}

# D-15: --setup flag early exit
if ($Setup) {
    Write-Output "Setup complete. Run .\run.ps1 to start the pipeline."
    exit 0
}

# D-13, D-03, D-11: Run phase — invoke pipeline
Write-Output "[Run] Starting pipeline..."
& $PythonExe -m src.main
