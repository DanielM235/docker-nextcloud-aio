"""
test_05_privacy_scan.py — guard against leaking personal data.

This repository is public, so committed files must contain only generic
values: no personal paths, no private/reserved IP addresses, no real
secrets, and no committed .env.
"""

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/project")
EXCLUDED_DIRS = {".git", "tests", "__pycache__", ".mypy_cache", ".venv", "venv"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tgz", ".tar"}

# Personal tokens from the development environment — must never be committed.
PERSONAL_TOKENS = ["LocalD", "dmla"]

# Loopback, "all interfaces", and Docker's documented default bridge network
# address (referenced in docs/NETWORKING.md) are not personal data.
ALLOWED_IPV4 = {"127.0.0.1", "0.0.0.0", "172.17.0.0"}

# Private / reserved IPv4 ranges (excluding loopback, which is allowed).
PRIVATE_IPV4 = re.compile(
    r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    r"|\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"
    r"|\b192\.168\.\d{1,3}\.\d{1,3}\b"
    r"|\b169\.254\.\d{1,3}\.\d{1,3}\b"
    r"|\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"
)

# 32+ hex chars ⇒ looks like a committed secret.
LONG_HEX = re.compile(r"\b[0-9a-fA-F]{32,}\b")


def _committed_text_files():
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(PROJECT_ROOT).parts)
        if parts & EXCLUDED_DIRS:
            continue
        # Local environment files are gitignored and never committed — they
        # are not part of the public repository surface.
        if path.name.startswith(".env"):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        yield path, text


class TestNoPersonalData:
    def test_no_personal_tokens(self):
        for path, text in _committed_text_files():
            for token in PERSONAL_TOKENS:
                assert token not in text, f"{token!r} found in {path}"

    def test_no_private_ipv4(self):
        for path, text in _committed_text_files():
            for match in PRIVATE_IPV4.findall(text):
                assert match in ALLOWED_IPV4, f"private IPv4 {match!r} found in {path}"

    def test_no_committed_secrets(self):
        for path, text in _committed_text_files():
            m = LONG_HEX.search(text)
            assert m is None, f"possible secret {m.group(0)!r} found in {path}"

    def test_env_ignored_and_untracked(self):
        # .env must be gitignored …
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert re.search(r"^\.env\s*$", gitignore, flags=re.M), (
            ".env must be listed in .gitignore"
        )
        # … and must not be tracked by git (never committed).
        result = subprocess.run(
            [
                "git", "-C", str(PROJECT_ROOT),
                "-c", "safe.directory=/project",
                "ls-files", "--error-unmatch", ".env",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, ".env must not be tracked by git"


class TestGenericConfigValues:
    def test_domain_placeholders(self):
        text = (PROJECT_ROOT / ".env.example").read_text()
        for key in ("DOMAIN_NAME", "AIO_ADMIN_HOSTNAME"):
            m = re.search(rf"^{key}=(.*)$", text, flags=re.M)
            assert m, f"{key} missing from .env.example"
            value = m.group(1).strip()
            assert value.endswith("example.com"), (
                f"{key} must use a generic example.com value, got {value!r}"
            )
