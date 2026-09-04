# Nextcloud (vanilla)

**Production Docker Compose configuration for a self-hosted Nextcloud built on
the official [`nextcloud`](https://hub.docker.com/_/nextcloud) image + MariaDB +
Redis.** No Docker socket access, no privileged orchestrator.

This is the **vanilla** alternative to the [AIO configuration](../aio). Choose
vanilla when you want full control over each service, host-level backups, and
no container with access to the Docker socket — accepting that you maintain
database, Redis, cron and upgrades yourself.

Target: **Debian 12 / Ubuntu 24.04**, with **nginx already installed at the OS
level** terminating TLS for the domain.

---

## Architecture

```
Internet
  │  :80 / :443
  ▼
System nginx (host, TLS termination)
  │  proxy_pass → http://127.0.0.1:APP_HTTP_PORT
  ▼
app  (nextcloud apache, loopback port only)
  ├── db      (MariaDB, internal network only)
  ├── redis   (cache + locking, internal network only)
  └── cron    (background jobs, internal network only)
```

Only `app` publishes a port, bound to `127.0.0.1`. `db`, `redis` and `cron`
have **no** published ports and live on the internal user-defined network.

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Docker Engine | ≥ 24 |
| Docker Compose v2 | ≥ 2.20 |
| System nginx (host) | recent |
| Debian 12 / Ubuntu 24.04 | — |

Also read the host hardening guide: [../docs/HOST_SECURITY.md](../docs/HOST_SECURITY.md).

---

## Quick start

### 1 — Install

```bash
cd vanilla
./setup.sh install --domain nextcloud.example.com --port 8080
```

`install` creates `.env` with auto-generated database secrets and pulls the
images. **No container is started.** Mount your external disk, then review
`.env` — `NEXTCLOUD_DATA_DIR` must point at it (`install` creates and chowns
that directory to `www-data`).

### 2 — Configure nginx

```bash
export NGINX_SERVER_NAME=nextcloud.example.com
export NGINX_APP_PORT=8080
export NGINX_SSL_CERT=/etc/letsencrypt/live/nextcloud.example.com/fullchain.pem
export NGINX_SSL_KEY=/etc/letsencrypt/live/nextcloud.example.com/privkey.pem
export NGINX_DHPARAM=/etc/nginx/dhparam
openssl dhparam -out "$NGINX_DHPARAM" 2048   # once
envsubst '${NGINX_SERVER_NAME} ${NGINX_APP_PORT} ${NGINX_SSL_CERT} ${NGINX_SSL_KEY} ${NGINX_DHPARAM}' \
  < nginx/templates/nextcloud.conf.template \
  > /etc/nginx/sites-available/nextcloud
ln -sf /etc/nginx/sites-available/nextcloud /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### 3 — Start

```bash
./setup.sh start
```

Then open `https://nextcloud.example.com` and complete the admin setup (or set
`NEXTCLOUD_ADMIN_USER` / `NEXTCLOUD_ADMIN_PASSWORD` in `.env` before `start` to
auto-install).

---

## Daily operations

```bash
./setup.sh status
./setup.sh logs app
./setup.sh occ maintenance:mode --on   # any occ command as www-data
./setup.sh backup                      # full backup (DB + data + config)
```

---

## Backup & restore

See [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

## Upgrading

See [docs/UPDATE.md](docs/UPDATE.md). Upgrades are **one major version at a
time** and are handled by the image's own migration on startup.

## Tests

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml \
  run --rm --build test-runner
```

## Layout

```
vanilla/
├── docker-compose.yml           ← production stack (db, redis, app, cron)
├── docker-compose.test.yml      ← test overlay
├── .env.example                 ← safe public template
├── setup.sh                     ← bootstrap / backup / update script
├── VERSION
├── nginx/
│   ├── nginx.conf
│   └── templates/nextcloud.conf.template
├── docs/
│   ├── ENV_VARS.md
│   ├── BACKUP_RESTORE.md
│   ├── UPDATE.md
│   └── SECURITY.md
└── tests/
```
