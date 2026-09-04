"""
test_05_privacy_scan.py — guard against leaking personal data (vanilla).

The repository is public: committed files must contain only generic values.
"""

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/project")   # = this config directory
REPO_ROOT = Path("/repo")         # = repository root (mounted read-only)

EXCLUDED_DIRS = {".git", "tests", "__pycache__", ".mypy_cache", ".venv", "venv"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tgz", ".tar"}

PERSONAL_TOKENS = ["LocalD", "dmla"]
ALLOWED_IPV4 = {"127.0.0.1", "0.0.0.0"}

PRIVATE_IPV4 = re.compile(
    r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    r"|\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"
    r"|\b192\.168\.\d{1,3}\.\d{1,3}\b"
    r"|\b169\.254\.\d{1,3}\.\d{1,3}\b"
    r"|\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"
)

LONG_HEX = re.compile(r"\b[0-9a-fA-F]{32,}\b")


def _committed_text_files():
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(PROJECT_ROOT).parts)
        if parts & EXCLUDED_DIRS:
            continue
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
        gitignore = (REPO_ROOT / ".gitignore").read_text()
        assert re.search(r"^\.env\s*$", gitignore, flags=re.M), ".env must be gitignored"
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "-c", "safe.directory=/repo", "ls-files"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        tracked = result.stdout.splitlines()
        assert not any(p.endswith(".env") for p in tracked), "no .env file may be tracked"


class TestGenericConfigValues:
    def test_domain_placeholder(self):
        text = (PROJECT_ROOT / ".env.example").read_text()
        m = re.search(r"^DOMAIN_NAME=(.*)$", text, flags=re.M)
        assert m and m.group(1).strip().endswith("example.com")
