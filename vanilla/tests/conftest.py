"""
conftest.py — Shared pytest fixtures and helpers for the vanilla Nextcloud
integration suite.

This is a "light" suite: it verifies the stack starts and the app responds,
plus static audits.  Tests that need the Docker daemon use the mounted socket
and skip cleanly when it is unavailable.
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

APP_HTTP_PORT = int(os.environ.get("APP_HTTP_PORT", "8080"))
COMPOSE_PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "nextcloud-vanilla")
TEST_TIMEOUT = int(os.environ.get("TEST_TIMEOUT", "180"))
RETRY_INTERVAL = int(os.environ.get("TEST_RETRY_INTERVAL", "5"))

# The app publishes a loopback port; the test-runner uses host networking.
APP_STATUS_URL = f"http://127.0.0.1:{APP_HTTP_PORT}/status.php"


def make_session(total_retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
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
