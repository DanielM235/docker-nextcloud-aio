# Reverse Proxy (nginx)

This repository is designed for a host where **nginx is already installed at
the OS level** and terminates TLS for all applications. Two server blocks are
provided:

| Template | Purpose | Upstream |
|----------|---------|----------|
| `nginx/templates/nextcloud.conf.template` | Nextcloud itself | `http://127.0.0.1:APACHE_PORT` |
| `nginx/templates/aio-admin.conf.template` | AIO admin interface | `https://127.0.0.1:AIO_INTERFACE_PORT` |

## 1 — Configure AIO for the reverse proxy

In `.env`, set:

```bash
APACHE_PORT=11000
APACHE_IP_BINDING=127.0.0.1   # nginx runs on the same host
```

- `APACHE_PORT` is the host port that AIO's Apache container publishes.
- `APACHE_IP_BINDING=127.0.0.1` restricts the Apache container to loopback;
  use `0.0.0.0` only if nginx runs on a different machine.

## 2 — Render and enable the Nextcloud vhost

```bash
export NGINX_SERVER_NAME=nextcloud.example.com
export NGINX_APACHE_PORT=11000
export NGINX_SSL_CERT=/etc/letsencrypt/live/nextcloud.example.com/fullchain.pem
export NGINX_SSL_KEY=/etc/letsencrypt/live/nextcloud.example.com/privkey.pem
export NGINX_DHPARAM=/etc/nginx/dhparam

envsubst '${NGINX_SERVER_NAME} ${NGINX_APACHE_PORT} ${NGINX_SSL_CERT} ${NGINX_SSL_KEY} ${NGINX_DHPARAM}' \
  < nginx/templates/nextcloud.conf.template \
  > /etc/nginx/sites-available/nextcloud

ln -sf /etc/nginx/sites-available/nextcloud /etc/nginx/sites-enabled/nextcloud
```

## 3 — (Recommended) Expose the AIO admin interface

The AIO interface uses a self-signed certificate on the mastercontainer. To
access it with a valid certificate, expose it on a dedicated hostname:

```bash
export NGINX_AIO_HOSTNAME=aio.example.com
export NGINX_AIO_PORT=8080            # must match AIO_INTERFACE_PORT
export NGINX_SSL_CERT=/etc/letsencrypt/live/aio.example.com/fullchain.pem
export NGINX_SSL_KEY=/etc/letsencrypt/live/aio.example.com/privkey.pem

envsubst '${NGINX_AIO_HOSTNAME} ${NGINX_AIO_PORT} ${NGINX_SSL_CERT} ${NGINX_SSL_KEY}' \
  < nginx/templates/aio-admin.conf.template \
  > /etc/nginx/sites-available/aio-admin

ln -sf /etc/nginx/sites-available/aio-admin /etc/nginx/sites-enabled/aio-admin
```

Alternatively, access the interface over an SSH tunnel:

```bash
ssh -L 8080:127.0.0.1:8080 user@your-server
# then open https://127.0.0.1:8080 in your browser
```

## 4 — Reload nginx

```bash
nginx -t && systemctl reload nginx
```

## 5 — TLS certificates (Certbot)

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d nextcloud.example.com -d aio.example.com
```

## Notes

- Nextcloud requires its **own dedicated domain** — it cannot run in a
  subdirectory.
- Do not publish AIO's ports `80` / `8443`; they are for AIO's integrated
  HTTPS mode, which conflicts with a host reverse proxy.
- If your reverse proxy connects to Nextcloud from an IP other than
  `localhost`/`127.0.0.1`, add that IP to Nextcloud's `trusted_proxies`.
