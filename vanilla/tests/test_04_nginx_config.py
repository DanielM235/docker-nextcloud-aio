"""
test_04_nginx_config.py — static validation of the vanilla nginx template.
"""

import re
from pathlib import Path

TEMPLATES = Path("/project/nginx/templates")
NEXTCLOUD = TEMPLATES / "nextcloud.conf.template"
NGINX_CONF = Path("/project/nginx/nginx.conf")


def _render(template: Path, **values) -> str:
    text = template.read_text()
    for key, value in values.items():
        text = text.replace("${" + key + "}", value)
    return text


class TestNextcloudTemplate:
    def test_proxy_pass(self):
        assert "proxy_pass http://127.0.0.1:${NGINX_APP_PORT}" in NEXTCLOUD.read_text()

    def test_forwarded_headers(self):
        text = NEXTCLOUD.read_text()
        for header in ("X-Forwarded-For", "X-Forwarded-Proto", "X-Forwarded-Host"):
            assert header in text, f"{header} missing"

    def test_hsts(self):
        assert "Strict-Transport-Security" in NEXTCLOUD.read_text()

    def test_dhparam(self):
        assert re.search(r"ssl_dhparam\s+\$\{NGINX_DHPARAM\}", NEXTCLOUD.read_text())

    def test_websocket(self):
        text = NEXTCLOUD.read_text()
        assert "map $http_upgrade $connection_upgrade" in text
        assert "Connection $connection_upgrade" in text

    def test_upload_size(self):
        assert "client_max_body_size 0" in NEXTCLOUD.read_text()

    def test_renders_without_placeholders(self):
        rendered = _render(
            NEXTCLOUD,
            NGINX_SERVER_NAME="nextcloud.example.com",
            NGINX_APP_PORT="8080",
            NGINX_SSL_CERT="/etc/letsencrypt/live/example/fullchain.pem",
            NGINX_SSL_KEY="/etc/letsencrypt/live/example/privkey.pem",
            NGINX_DHPARAM="/etc/nginx/dhparam",
        )
        assert "${" not in rendered


class TestMainNginxConf:
    def test_main_conf(self):
        text = NGINX_CONF.read_text()
        assert "include /etc/nginx/conf.d/*.conf" in text
        assert "client_max_body_size 0" in text
        assert re.search(r"server_tokens\s+off", text)
