"""
test_04_nginx_config.py — static validation of the nginx templates.

Verifies that the two virtual-host templates contain every directive the
Nextcloud AIO reverse proxy requires, and that they render completely with
envsubst-style variable substitution.
"""

import re
from pathlib import Path

TEMPLATES = Path("/project/nginx/templates")
NEXTCLOUD = TEMPLATES / "nextcloud.conf.template"
AIO_ADMIN = TEMPLATES / "aio-admin.conf.template"
NGINX_CONF = Path("/project/nginx/nginx.conf")


def _render(template: Path, **values) -> str:
    text = template.read_text()
    for key, value in values.items():
        text = text.replace("${" + key + "}", value)
    return text


class TestNextcloudTemplate:
    def test_websocket_map(self):
        assert "map $http_upgrade $connection_upgrade" in NEXTCLOUD.read_text()

    def test_proxy_pass_to_apache(self):
        assert "proxy_pass http://127.0.0.1:${NGINX_APACHE_PORT}$request_uri" in NEXTCLOUD.read_text()

    def test_upload_and_buffering(self):
        text = NEXTCLOUD.read_text()
        assert "client_max_body_size 0" in text
        assert "proxy_buffering off" in text
        assert "proxy_request_buffering off" in text

    def test_forwarded_headers(self):
        text = NEXTCLOUD.read_text()
        for header in (
            "X-Forwarded-Host",
            "X-Forwarded-Proto",
            "X-Forwarded-Port",
            "X-Forwarded-For",
            "X-Real-IP",
        ):
            assert header in text, f"{header} missing"

    def test_websocket_headers(self):
        text = NEXTCLOUD.read_text()
        assert "Upgrade    $http_upgrade" in text
        assert "Connection $connection_upgrade" in text

    def test_read_timeout(self):
        assert "proxy_read_timeout 3610s" in NEXTCLOUD.read_text()

    def test_renders_without_placeholders(self):
        rendered = _render(
            NEXTCLOUD,
            NGINX_SERVER_NAME="nextcloud.example.com",
            NGINX_APACHE_PORT="11000",
            NGINX_SSL_CERT="/etc/letsencrypt/live/example/fullchain.pem",
            NGINX_SSL_KEY="/etc/letsencrypt/live/example/privkey.pem",
            NGINX_DHPARAM="/etc/nginx/dhparam",
        )
        assert "${" not in rendered


class TestAioAdminTemplate:
    def test_proxy_to_interface(self):
        text = AIO_ADMIN.read_text()
        assert "proxy_pass https://127.0.0.1:${NGINX_AIO_PORT}" in text
        assert "proxy_ssl_verify off" in text

    def test_renders_without_placeholders(self):
        rendered = _render(
            AIO_ADMIN,
            NGINX_AIO_HOSTNAME="aio.example.com",
            NGINX_AIO_PORT="8080",
            NGINX_SSL_CERT="/etc/letsencrypt/live/example/fullchain.pem",
            NGINX_SSL_KEY="/etc/letsencrypt/live/example/privkey.pem",
        )
        assert "${" not in rendered


class TestMainNginxConf:
    def test_main_conf(self):
        text = NGINX_CONF.read_text()
        assert "include /etc/nginx/conf.d/*.conf" in text
        assert "client_max_body_size 0" in text
        assert re.search(r"server_tokens\s+off", text)
