"""
test_03_setup_sh.py — setup.sh lifecycle using a fake docker binary.

These tests never touch the real Docker daemon.
"""

import re

from support import run_setup, env_value, set_env_value


class TestInstall:
    def test_install_creates_env(self, workspace):
        result = run_setup(workspace, "install")
        assert result.returncode == 0
        env_path = workspace / ".env"
        assert env_path.exists()

    def test_install_no_placeholder_secrets(self, workspace):
        run_setup(workspace, "install")
        text = (workspace / ".env").read_text()
        assert "CHANGE_ME" not in text

    def test_install_generates_no_secrets(self, workspace):
        # Nextcloud AIO creates its own secrets internally — .env must stay
        # free of any long random hex string.
        run_setup(workspace, "install")
        text = (workspace / ".env").read_text()
        assert not re.search(r"[0-9a-fA-F]{32,}", text)

    def test_install_domain_override(self, workspace):
        run_setup(workspace, "install", "--domain", "cloud.example.com")
        assert env_value(workspace, "DOMAIN_NAME") == "cloud.example.com"

    def test_install_port_overrides(self, workspace):
        run_setup(workspace, "install", "--apache-port", "12000", "--aio-port", "9090")
        assert env_value(workspace, "APACHE_PORT") == "12000"
        assert env_value(workspace, "AIO_INTERFACE_PORT") == "9090"

    def test_install_is_idempotent(self, workspace):
        run_setup(workspace, "install")
        set_env_value(workspace, "DOMAIN_NAME", "kept.example.com")
        result = run_setup(workspace, "install")
        assert result.returncode == 0
        assert env_value(workspace, "DOMAIN_NAME") == "kept.example.com"


class TestValidation:
    def test_rejects_invalid_domain(self, workspace):
        result = run_setup(workspace, "install", "--domain", "bad|domain.com")
        assert result.returncode != 0
        assert "Invalid domain" in result.stderr

    def test_rejects_invalid_port(self, workspace):
        result = run_setup(workspace, "install", "--apache-port", "99999")
        assert result.returncode != 0
        assert "Invalid Apache port" in result.stderr

    def test_rejects_invalid_project_name(self, workspace):
        result = run_setup(workspace, "install", "--project-name", "Bad_Name!")
        assert result.returncode != 0
        assert "Invalid project name" in result.stderr


class TestLifecycle:
    def test_start_requires_env(self, workspace):
        result = run_setup(workspace, "start")
        assert result.returncode != 0
        assert ".env not found" in result.stderr

    def test_start_status_stop(self, workspace):
        run_setup(workspace, "install")
        assert run_setup(workspace, "start").returncode == 0
        assert run_setup(workspace, "status").returncode == 0
        assert run_setup(workspace, "stop").returncode == 0

    def test_backup_triggers_docker_exec(self, workspace):
        run_setup(workspace, "install")
        log = workspace / "calls.log"
        result = run_setup(workspace, "backup", extra_env={"DOCKER_LOG": str(log)})
        assert result.returncode == 0
        calls = log.read_text()
        assert "exec" in calls
        assert "nextcloud-aio-mastercontainer" in calls
        assert "/daily-backup.sh" in calls
