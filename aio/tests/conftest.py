"""
conftest.py — Shared pytest fixtures and helpers.

This is a "light" integration suite: it does NOT attempt a full Nextcloud
bootstrap (which requires a real domain + Let's Encrypt).  It verifies that
the mastercontainer starts and serves its AIO interface, plus static audits
of the Compose file, nginx templates and repository hygiene.

Tests that need the Docker daemon use the mounted socket and skip cleanly
when it is unavailable.
"""

import os
import time

import pytest
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from support import build_workspace

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------------------------------------------------------
# Configuration — supplied via environment (docker-compose.test.yml)
# ----------------------------------------------------------------
AIO_INTERFACE_PORT   = int(os.environ.get("AIO_INTERFACE_PORT", "8080"))
AIO_MASTER_CONTAINER = os.environ.get("AIO_MASTER_CONTAINER", "nextcloud-aio-mastercontainer")
NGINX_TEST_CONTAINER = os.environ.get("NGINX_TEST_CONTAINER", "nextcloud-aio-nginx-test")
TEST_TIMEOUT         = int(os.environ.get("TEST_TIMEOUT", "180"))
RETRY_INTERVAL       = int(os.environ.get("TEST_RETRY_INTERVAL", "5"))

# The AIO interface is published on the host loopback by default; the
# test-runner uses host networking so 127.0.0.1 is the Docker host.
AIO_INTERFACE_URL = f"https://127.0.0.1:{AIO_INTERFACE_PORT}/"


def make_session(total_retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    """Return a requests.Session with retry logic baked in."""
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def wait_for_url(url, *, timeout=TEST_TIMEOUT, interval=RETRY_INTERVAL, expected=(200,)):
    """Block until *url* returns one of *expected* status codes (self-signed OK)."""
    session = make_session()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = session.get(url, verify=False, allow_redirects=False, timeout=10)
            if resp.status_code in expected:
                return resp
        except requests.RequestException:
            pass
        time.sleep(interval)
    pytest.fail(f"URL {url!r} did not return HTTP {expected} within {timeout}s")


# ----------------------------------------------------------------
# Docker client (uses the mounted socket)
# ----------------------------------------------------------------
def _docker_client():
    try:
        import docker  # noqa: F401
        return docker.from_env()
    except Exception:
        return None


@pytest.fixture(scope="session")
def docker_client():
    client = _docker_client()
    if client is None:
        pytest.skip("Docker socket not available — skipping container tests")
    return client


@pytest.fixture()
def workspace(tmp_path):
    """Isolated project copy with a fake docker binary on PATH."""
    return build_workspace(tmp_path)
