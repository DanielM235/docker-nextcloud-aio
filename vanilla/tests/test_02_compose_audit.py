"""
test_02_compose_audit.py — static security/config audit of the vanilla
docker-compose.yml.
"""

from pathlib import Path

import pytest
import yaml

COMPOSE_FILE = Path("/project/docker-compose.yml")
SERVICES = ["db", "redis", "app", "cron"]


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text())


class TestServices:
    def test_service_set(self, compose):
        assert set(compose["services"].keys()) == set(SERVICES)

    def test_no_docker_socket(self, compose):
        for name, svc in compose["services"].items():
            vols = svc.get("volumes", []) or []
            assert not any("docker.sock" in v for v in vols), (
                f"{name} must not mount the Docker socket"
            )

    def test_only_app_publishes_loopback_port(self, compose):
        for name, svc in compose["services"].items():
            if name == "app":
                ports = svc.get("ports", [])
                assert len(ports) == 1
                assert ports[0].startswith("127.0.0.1:"), "app port must be loopback-bound"
            else:
                assert "ports" not in svc, f"{name} must not publish any port"

    def test_app_has_no_user_override(self, compose):
        # The image drops to www-data internally; we must not override it.
        assert "user" not in compose["services"]["app"]

    def test_images_not_latest(self, compose):
        for name, svc in compose["services"].items():
            assert "latest" not in svc["image"], f"{name} image must be pinned"

    def test_redis_requirepass(self, compose):
        command = compose["services"]["redis"]["command"]
        assert "--requirepass" in command, "redis must enforce a password"

    def test_app_has_redis_password(self, compose):
        env = compose["services"]["app"].get("environment", {})
        assert "REDIS_HOST_PASSWORD" in env, "app must receive REDIS_HOST_PASSWORD"


class TestHardening:
    def test_cap_drop_all(self, compose):
        # `app` intentionally keeps default capabilities (the image entrypoint
        # needs them for the first-boot rsync); see docs/SECURITY.md.
        for name, svc in compose["services"].items():
            if name == "app":
                assert "cap_drop" not in svc, "app must NOT drop capabilities"
                continue
            assert "ALL" in svc.get("cap_drop", []), f"{name} must drop all capabilities"

    def test_no_new_privileges(self, compose):
        for name, svc in compose["services"].items():
            opts = svc.get("security_opt", [])
            assert "no-new-privileges:true" in opts, f"{name} missing no-new-privileges"

    def test_resource_limits(self, compose):
        for name, svc in compose["services"].items():
            limits = svc["deploy"]["resources"]["limits"]
            assert "memory" in limits, f"{name} missing memory limit"
            assert "cpus" in limits, f"{name} missing cpu limit"

    def test_healthchecks(self, compose):
        for name in ("db", "redis", "app"):
            assert compose["services"][name].get("healthcheck", {}).get("test"), (
                f"{name} missing healthcheck"
            )


class TestConfig:
    def test_env_example_pins_version(self):
        text = (Path("/project/.env.example")).read_text()
        assert "NEXTCLOUD_IMAGE_TAG=34.0.3-apache" in text

    def test_docs_exist(self):
        for name in ("ENV_VARS", "BACKUP_RESTORE", "UPDATE", "SECURITY"):
            assert (Path("/project/docs") / f"{name}.md").exists(), f"missing docs/{name}.md"
