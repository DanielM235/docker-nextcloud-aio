"""
support.py — Shared helpers for setup.sh unit tests.

These tests exercise setup.sh in an isolated temporary directory with a
minimal fake `docker` binary placed earlier on PATH.  They never call the
real Docker daemon.
"""

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

# ----------------------------------------------------------------
# Project-root paths (mounted read-only at /project by compose)
# ----------------------------------------------------------------
PROJECT_ROOT = Path("/project")
SETUP_SH     = PROJECT_ROOT / "setup.sh"
ENV_EXAMPLE  = PROJECT_ROOT / ".env.example"
VERSION_FILE = PROJECT_ROOT / "VERSION"


# ----------------------------------------------------------------
# Fake docker binary
#
# Handles every docker / docker compose call that setup.sh makes:
#   docker version --format '...'     → version string (prerequisites check)
#   docker compose version            → compose version string
#   docker compose ... pull/up/down/… → noop (exit 0)
#   docker exec ...                   → noop (exit 0)
# ----------------------------------------------------------------
DOCKER_STUB = textwrap.dedent("""\
    #!/usr/bin/env bash
    # Log every invocation (all args on one line) when DOCKER_LOG is set.
    if [[ -n "${DOCKER_LOG:-}" ]]; then
        echo "$*" >> "${DOCKER_LOG}"
    fi
    if [[ "${1:-}" == "version" ]]; then
        echo "26.0.0"
        exit 0
    fi
    if [[ "${1:-}" == "compose" && "${2:-}" == "version" ]]; then
        echo "Docker Compose version v2.24.0"
        exit 0
    fi
    # All other sub-commands succeed silently
    exit 0
""")


# ----------------------------------------------------------------
# Workspace builder (used by the `workspace` fixture in conftest.py)
# ----------------------------------------------------------------
def build_workspace(tmp_path: Path) -> Path:
    """
    Populate a fresh temp directory with everything setup.sh needs:
      - setup.sh   (executable copy from /project)
      - .env.example
      - VERSION
      - docker-compose.yml       (empty stub — never parsed in these tests)
      - docker-compose.test.yml  (empty stub)
      - bin/docker               (fake docker binary)
    """
    shutil.copy(SETUP_SH, tmp_path / "setup.sh")
    shutil.copy(ENV_EXAMPLE, tmp_path / ".env.example")
    shutil.copy(VERSION_FILE, tmp_path / "VERSION")
    (tmp_path / "setup.sh").chmod(0o755)

    (tmp_path / "docker-compose.yml").write_text("# stub\n")
    (tmp_path / "docker-compose.test.yml").write_text("# stub\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_stub = bin_dir / "docker"
    docker_stub.write_text(DOCKER_STUB)
    docker_stub.chmod(0o755)

    return tmp_path


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def run_setup(
    workspace: Path,
    *args: str,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    """
    Execute setup.sh inside *workspace* with the fake docker on PATH.
    Returns the CompletedProcess (stdout + stderr captured, text mode).
    Never raises on non-zero exit — callers assert the exit code.
    """
    env = os.environ.copy()
    env["PATH"] = str(workspace / "bin") + ":" + env.get(
        "PATH",
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    )
    # Prevent ambient host variables from leaking into .env generation.
    for var in ("COMPOSE_PROJECT_NAME", "DOMAIN_NAME", "AIO_INTERFACE_PORT", "APACHE_PORT"):
        env.pop(var, None)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(workspace / "setup.sh")] + list(args),
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
    )


def env_value(workspace: Path, key: str) -> str | None:
    """Return the value of *key* from workspace/.env, or None."""
    env_path = workspace / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return None


def set_env_value(workspace: Path, key: str, value: str) -> None:
    """Set (or replace) a KEY=VALUE line in workspace/.env."""
    env_path = workspace / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    out = []
    replaced = False
    for line in lines:
        if line.startswith(f"{key}="):
            if not replaced:
                out.append(f"{key}={value}")
                replaced = True
            # drop duplicate lines for this key
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    env_path.write_text("\n".join(out) + "\n")


def docker_calls(log_file: Path) -> list[str]:
    """Return the list of fake-docker invocations recorded in *log_file*."""
    if not log_file.exists():
        return []
    return log_file.read_text().splitlines()
