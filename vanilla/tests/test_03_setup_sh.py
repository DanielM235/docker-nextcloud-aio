"""
test_03_setup_sh.py — vanilla setup.sh lifecycle using a fake docker binary.
"""

import re

from support import run_setup, env_value, set_env_value


class TestInstall:
    def test_install_creates_env(self, workspace):
        result = run_setup(workspace, "install")
        assert result.returncode == 0
        assert (workspace / ".env").exists()

    def test_install_generates_secrets(self, workspace):
        run_setup(workspace, "install")
        text = (workspace / ".env").read_text()
        assert "CHANGE_ME" not in text
        for key in ("MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "REDIS_HOST_PASSWORD"):
            value = env_value(workspace, key)
            assert value and re.fullmatch(r"[0-9a-f]{48}", value), f"{key} must be generated"

    def test_install_domain_override(self, workspace):
        run_setup(workspace, "install", "--domain", "cloud.example.com")
        assert env_value(workspace, "DOMAIN_NAME") == "cloud.example.com"
        assert env_value(workspace, "OVERWRITECLIURL") == "https://cloud.example.com"

    def test_install_port_override(self, workspace):
        run_setup(workspace, "install", "--port", "9090")
        assert env_value(workspace, "APP_HTTP_PORT") == "9090"

    def test_install_is_idempotent(self, workspace):
        run_setup(workspace, "install")
        set_env_value(workspace, "DOMAIN_NAME", "kept.example.com")
        assert run_setup(workspace, "install").returncode == 0
        assert env_value(workspace, "DOMAIN_NAME") == "kept.example.com"


class TestValidation:
    def test_rejects_invalid_domain(self, workspace):
        result = run_setup(workspace, "install", "--domain", "bad|domain.com")
        assert result.returncode != 0
        assert "Invalid domain" in result.stderr

    def test_rejects_invalid_port(self, workspace):
        result = run_setup(workspace, "install", "--port", "99999")
        assert result.returncode != 0


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
