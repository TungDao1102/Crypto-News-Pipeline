from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestDockerfile:

    def test_exists(self):
        assert (REPO_ROOT / "Dockerfile").exists()

    def test_from_python_slim(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "FROM python:" in content
        assert "slim" in content

    def test_single_from_statement(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert content.count("FROM ") == 1

    def test_has_entrypoint(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "ENTRYPOINT" in content

    def test_has_workdir(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "WORKDIR /app" in content

    def test_pip_no_cache_dir(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "--no-cache-dir" in content

    def test_pythonunbuffered_set(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert "PYTHONUNBUFFERED=1" in content

    def test_has_labels(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        labels = [line for line in content.split("\n") if line.strip().startswith("LABEL")]
        assert len(labels) >= 2

    def test_copy_src_after_pip(self):
        content = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        pip_index = content.index("pip install")
        copy_src_index = content.index("COPY src/")
        assert copy_src_index > pip_index


class TestEntrypoint:

    def test_exists(self):
        assert (REPO_ROOT / "entrypoint.sh").exists()

    def test_has_shebang(self):
        content = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/sh")

    def test_set_e(self):
        content = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
        assert "set -e" in content

    def test_checks_env_exists(self):
        content = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
        assert ".env" in content

    def test_checks_sources_json_exists(self):
        content = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
        assert "sources.json" in content

    def test_placeholder_detection(self):
        content = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
        assert "your_" in content

    def test_exec_python_main(self):
        content = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
        assert "exec python -m src.main" in content

    def test_creates_logs_and_session_dirs(self):
        content = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
        assert "mkdir -p logs" in content
        assert "mkdir -p session" in content


class TestDotDockerignore:

    def test_exists(self):
        assert (REPO_ROOT / ".dockerignore").exists()

    def test_excludes_env(self):
        content = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        assert ".env" in content

    def test_excludes_git(self):
        content = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        assert ".git/" in content or ".git" in content

    def test_excludes_pycache(self):
        content = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        assert "__pycache__" in content

    def test_excludes_tests(self):
        content = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        assert "tests/" in content or "tests" in content


class TestRuffToml:

    def test_exists(self):
        assert (REPO_ROOT / ".ruff.toml").exists()

    def test_valid_toml(self):
        import tomllib
        data = tomllib.load((REPO_ROOT / ".ruff.toml").open("rb"))
        assert "target-version" in data
        assert "lint" in data

    def test_target_py314(self):
        import tomllib
        data = tomllib.load((REPO_ROOT / ".ruff.toml").open("rb"))
        assert data["target-version"] == "py314"

    def test_lint_select_contains_e(self):
        import tomllib
        data = tomllib.load((REPO_ROOT / ".ruff.toml").open("rb"))
        select = data.get("lint", {}).get("select", [])
        assert "E" in select


class TestDockerCompose:

    def test_exists(self):
        assert (REPO_ROOT / "docker-compose.yml").exists()

    def test_valid_yaml(self):
        import yaml
        with (REPO_ROOT / "docker-compose.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_has_pipeline_service(self):
        import yaml
        with (REPO_ROOT / "docker-compose.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "pipeline" in data.get("services", {})

    def test_restart_unless_stopped(self):
        import yaml
        with (REPO_ROOT / "docker-compose.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["services"]["pipeline"].get("restart") == "unless-stopped"

    def test_has_env_file(self):
        import yaml
        with (REPO_ROOT / "docker-compose.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "env_file" in data["services"]["pipeline"]

    def test_has_healthcheck(self):
        import yaml
        with (REPO_ROOT / "docker-compose.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "healthcheck" in data["services"]["pipeline"]


class TestDeployWorkflow:

    def test_exists(self):
        assert (REPO_ROOT / ".github/workflows/deploy.yml").exists()

    def test_valid_yaml(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_has_ci_job(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "ci" in data.get("jobs", {})

    def test_has_cd_job(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "cd" in data.get("jobs", {})

    def test_cd_needs_ci(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "ci" in data["jobs"]["cd"].get("needs", [])

    def test_has_workflow_dispatch(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        on_key = "on" if "on" in data else True
        assert "workflow_dispatch" in data.get(on_key, {})

    def test_has_ssh_action(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        steps = data["jobs"]["cd"].get("steps", [])
        ssh_steps = [s for s in steps if "ssh-action" in s.get("uses", "")]
        assert len(ssh_steps) == 1

    def test_has_docker_build_push(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        steps = data["jobs"]["cd"].get("steps", [])
        build_steps = [s for s in steps if "build-push-action" in s.get("uses", "")]
        assert len(build_steps) == 1

    def test_concurrency_cancel_in_progress(self):
        import yaml
        with (REPO_ROOT / ".github/workflows/deploy.yml").open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        concurrency = data.get("concurrency", {})
        assert concurrency.get("cancel-in-progress") is True


class TestDEPLOYMENT:

    def test_exists(self):
        assert (REPO_ROOT / "DEPLOYMENT.md").exists()

    def test_minimum_length(self):
        content = (REPO_ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert len(content.split("\n")) >= 80

    def test_contains_prerequisites(self):
        content = (REPO_ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert "Prerequisites" in content or "prerequisites" in content.lower()

    def test_contains_secrets_table(self):
        content = (REPO_ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert "DOCKERHUB_USERNAME" in content
        assert "SSH_HOST" in content

    def test_contains_troubleshooting_section(self):
        content = (REPO_ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
        assert "Troubleshooting" in content or "troubleshooting" in content.lower()
