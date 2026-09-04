"""
test_02_compose_audit.py — static security/config audit of docker-compose.yml.

Parses the production Compose file and asserts the invariants that prevent
regressions (fixed upstream names, no published 80/8443, resource limits,
hardening attributes, healthcheck).
"""

from pathlib import Path

import pytest
import yaml

COMPOSE_FILE = Path("/project/docker-compose.yml")
SERVICE = "nextcloud-aio-mastercontainer"


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text())


def _env(svc: dict) -> dict:
    return svc.get("environment", {}) or {}


class TestTopLevel:
    def test_project_name_declared(self, compose):
        assert "name" in compose

    def test_single_service(self, compose):
        assert set(compose["services"].keys()) == {SERVICE}


class TestMastercontainer:
    def test_fixed_container_name(self, compose):
        svc = compose["services"][SERVICE]
        assert svc["container_name"] == "nextcloud-aio-mastercontainer"

    def test_image_channel_tag_parameterized(self, compose):
        image = compose["services"][SERVICE]["image"]
        assert "all-in-one:${AIO_IMAGE_TAG" in image

    def test_fixed_volume_name(self, compose):
        vols = compose["services"][SERVICE]["volumes"]
        assert "nextcloud_aio_mastercontainer:/mnt/docker-aio-config" in vols
        assert compose["volumes"]["nextcloud_aio_mastercontainer"]["name"] == "nextcloud_aio_mastercontainer"

    def test_docker_socket_readonly(self, compose):
        vols = compose["services"][SERVICE]["volumes"]
        assert any(v.endswith("/var/run/docker.sock:ro") for v in vols)

    def test_only_interface_port_published(self, compose):
        ports = compose["services"][SERVICE]["ports"]
        assert len(ports) == 1
        # 80 and 8443 must NOT be published (behind a reverse proxy).
        assert not any(p.endswith(":80") or p.endswith(":8443") for p in ports)

    def test_required_env(self, compose):
        env = _env(compose["services"][SERVICE])
        for var in (
            "APACHE_PORT",
            "APACHE_IP_BINDING",
            "SKIP_DOMAIN_VALIDATION",
            "NEXTCLOUD_UPLOAD_LIMIT",
            "WATCHTOWER_DOCKER_SOCKET_PATH",
        ):
            assert var in env, f"{var} missing from environment"


class TestHardening:
    def test_resource_limits(self, compose):
        limits = compose["services"][SERVICE]["deploy"]["resources"]["limits"]
        for key in ("cpus", "memory", "pids"):
            assert key in limits, f"missing {key} limit"

    def test_logging(self, compose):
        options = compose["services"][SERVICE]["logging"]["options"]
        assert "max-size" in options
        assert "max-file" in options

    def test_restart_policy(self, compose):
        assert compose["services"][SERVICE].get("restart")

    def test_security_opt(self, compose):
        opts = compose["services"][SERVICE].get("security_opt", [])
        assert "no-new-privileges:true" in opts

    def test_no_cap_drop(self, compose):
        # The mastercontainer is a privileged orchestrator; a full
        # cap_drop: ALL breaks its entrypoint (verified).  Documented in
        # docs/SECURITY_AUDIT.md — assert the decision is not regressed.
        assert "cap_drop" not in compose["services"][SERVICE]

    def test_healthcheck(self, compose):
        assert compose["services"][SERVICE].get("healthcheck", {}).get("test")


class TestDocs:
    def test_docs_exist(self):
        for name in (
            "ARCHITECTURE",
            "ENV_VARS",
            "BACKUP_RESTORE",
            "SECURITY_AUDIT",
            "TROUBLESHOOTING",
            "REVERSE_PROXY",
            "NETWORKING",
        ):
            assert (Path("/project/docs") / f"{name}.md").exists(), f"missing docs/{name}.md"
