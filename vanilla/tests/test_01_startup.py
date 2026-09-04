"""
test_01_startup.py — the vanilla stack must start: db, redis, app and cron
must all reach "running", and the app must answer on its status endpoint.
"""

import time

from conftest import APP_STATUS_URL, COMPOSE_PROJECT, TEST_TIMEOUT, RETRY_INTERVAL, wait_for_url

SERVICES = ["db", "redis", "app", "cron"]


def _wait_for_container(docker_client, name, timeout=TEST_TIMEOUT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            container = docker_client.containers.get(name)
            if container.status == "running":
                return container
        except Exception:
            pass
        time.sleep(RETRY_INTERVAL)
    raise AssertionError(f"Container {name!r} did not reach 'running' within {timeout}s")


class TestStartup:
    def test_services_running(self, docker_client):
        for svc in SERVICES:
            container = _wait_for_container(docker_client, f"{COMPOSE_PROJECT}-{svc}")
            assert container.status == "running", f"{svc} is not running"

    def test_app_status_endpoint(self, docker_client):
        # status.php returns 200 with {"installed":...} once Apache is up
        # (before or after the first-run install completes).
        wait_for_url(APP_STATUS_URL, expected=(200,))
