from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestRunPs1:

    def test_exists(self):
        assert (REPO_ROOT / "run.ps1").exists()

    def test_ps1_extension(self):
        assert (REPO_ROOT / "run.ps1").suffix == ".ps1"

    def test_has_param_block(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "param(" in content

    def test_has_help_switch(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "$Help" in content

    def test_has_setup_switch(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "$Setup" in content

    def test_python_installed_check(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "Get-Command" in content
        assert "python" in content

    def test_python_version_check(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "3.14" in content

    def test_venv_auto_create(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "-m venv" in content

    def test_pip_install(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "pip install" in content

    def test_gitignore_modification(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert ".gitignore" in content

    def test_pipeline_start_cmd(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "src.main" in content

    def test_no_dir_precreation_logs(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        code_lines = [line for line in content.split("\n") if not line.strip().startswith("#")]
        assert not any("mkdir" in line and "logs" in line for line in code_lines)
        assert not any("mkdir" in line and ".session" in line for line in code_lines)

    def test_no_dir_precreation_via_newitem(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        code_lines = [line for line in content.split("\n") if not line.strip().startswith("#")]
        assert not any("New-Item" in line and "logs" in line for line in code_lines)
        assert not any("New-Item" in line and ".session" in line for line in code_lines)

    def test_no_duplicated_validation(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        code_lines = [line for line in content.split("\n") if not line.strip().startswith("#")]
        code = "\n".join(code_lines)
        assert "grep" not in code
        assert "your_" not in code

    def test_has_synopsis_comment(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert ".SYNOPSIS" in content

    def test_minimum_length(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert len(content.split("\n")) >= 80

    def test_uses_join_path(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "Join-Path" in content

    def test_uses_erroraction_preference(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert "$ErrorActionPreference" in content

    def test_session_referenced(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert ".session" in content

    def test_venv_path_constructed(self):
        content = (REPO_ROOT / "run.ps1").read_text(encoding="utf-8")
        assert ".venv" in content


class TestGitignore:

    def test_exists(self):
        assert (REPO_ROOT / ".gitignore").exists()

    def test_session_dir_ignored(self):
        content = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".session/" in content

    def test_venv_ignored(self):
        content = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".venv" in content
