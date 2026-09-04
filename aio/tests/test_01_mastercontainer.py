"""
test_01_mastercontainer.py — the mastercontainer must start and serve its
AIO interface (self-signed HTTPS), and the mirrored nginx container must load
our production nginx configuration.
"""

import time

from conftest import (
    AIO_INTERFACE_URL,
    AIO_MASTER_CONTAINER,
    NGINX_TEST_CONTAINER,
    TEST_TIMEOUT,
    RETRY_INTERVAL,
    wait_for_url,
)


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


class TestMastercontainer:
    def test_mastercontainer_running(self, docker_client):
        container = _wait_for_container(docker_client, AIO_MASTER_CONTAINER)
        assert container.status == "running"

    def test_aio_interface_reachable(self, docker_client):
        # The AIO interface serves self-signed HTTPS.  The root path returns a
        # redirect (302) before setup; any 2xx/3xx proves the interface is up.
        wait_for_url(
            AIO_INTERFACE_URL,
            expected=(200, 301, 302, 303, 307, 308),
        )

    def test_nginx_test_container_runs(self, docker_client):
        # nginx-test only stays up if nginx.conf + the rendered templates are
        # syntactically valid, so a running container proves the config loads.
        container = _wait_for_container(docker_client, NGINX_TEST_CONTAINER)
        assert container.status == "running"
