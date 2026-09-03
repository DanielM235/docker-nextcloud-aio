# nextcloud-aio

**Production Docker Compose configuration for
[Nextcloud AIO (All-in-One)](https://github.com/nextcloud/all-in-one).**

This repository packages Nextcloud AIO into a hardened, production-ready Docker
Compose setup designed for a **Debian 12 / Ubuntu 24.04 server** that already
runs **nginx at the OS level** as a central reverse proxy for many
applications. TLS is terminated by that nginx, which forwards HTTPS to AIO.

> Nextcloud AIO is orchestrated by a single **mastercontainer** that talks to
> the Docker socket and creates all other containers (Nextcloud, Apache,
> PostgreSQL, Redis, …) by itself. This repository defines that one service,
> plus the reverse-proxy configuration and operational tooling around it.

---

## Project version

This configuration wrapper is versioned independently from Nextcloud itself.
The current version is stored in [`VERSION`](VERSION):

```bash
cat VERSION
```

The AIO image channel is controlled by `AIO_IMAGE_TAG` in `.env` (default:
`latest` — the stable channel). Nextcloud AIO ships rolling channels, not
semantic versions, so updates are managed by AIO itself (see
[Updating](#updating-nextcloud-aio)).

---

## Architecture overview

```
Internet
  │
  ▼  :80 / :443
┌──────────────────────────────────────────────┐
│  System nginx  (Debian 12 / Ubuntu 24.04)    │  TLS termination
│  vhosts: nextcloud + aio-admin               │  WebSocket upgrade
└──────┬───────────────────────────┬───────────┘
       │ proxy→ 127.0.0.1:11000    │ proxy→ https://127.0.0.1:8080
       ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────────────┐
│  nextcloud-aio-apache    │  │  nextcloud-aio-mastercontainer   │
│  (created by AIO)        │  │  AIO web interface (self-signed) │
└──────────┬───────────────┘  └───────────┬──────────────────────┘
           │                              │ Docker socket (ro)
           ▼                              ▼
   Nextcloud + PostgreSQL + Redis + …   (orchestrates all siblings)
   (all created and managed by AIO on the "nextcloud-aio" network)
```

Full details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Prerequisites

| Requirement | Minimum version |
|-------------|----------------|
| Docker Engine | ≥ 24 |
| Docker Compose v2 plugin | ≥ 2.20 |
| System nginx | recent (already installed on host) |
| Debian 12 / Ubuntu 24.04 host | — |

```bash
# Verify
docker version
docker compose version
nginx -v
```

---

## Quick start

### 1 — Clone

```bash
git clone https://github.com/your-org/nextcloud-aio.git
cd nextcloud-aio
```

### 2 — Install

Run `install` once per instance. It creates `.env` and pulls the image.
**No container is ever started by `install`** — inspect `.env` and configure
nginx first.

```bash
./setup.sh install \
  --domain       nextcloud.example.com \
  --apache-port  11000
```

| Option | Short | What it sets in `.env` |
|--------|-------|------------------------|
| `--project-name NAME` | `-p` | `COMPOSE_PROJECT_NAME` (only scopes this Compose project) |
| `--domain DOMAIN` | `-d` | `DOMAIN_NAME` |
| `--aio-port PORT` | | `AIO_INTERFACE_PORT` — the AIO interface host port |
| `--apache-port PORT` | | `APACHE_PORT` — the port nginx proxies to |

There are **no secrets to generate** — Nextcloud AIO creates its own passwords
internally during setup. Review `.env` (especially `DOMAIN_NAME`), then see
[docs/ENV_VARS.md](docs/ENV_VARS.md).

### 3 — Configure system nginx

Render the two virtual-host templates and enable them on the host:

```bash
# Nextcloud vhost
export NGINX_SERVER_NAME=nextcloud.example.com
export NGINX_APACHE_PORT=11000
export NGINX_SSL_CERT=/etc/letsencrypt/live/nextcloud.example.com/fullchain.pem
export NGINX_SSL_KEY=/etc/letsencrypt/live/nextcloud.example.com/privkey.pem
export NGINX_DHPARAM=/etc/nginx/dhparam
envsubst '${NGINX_SERVER_NAME} ${NGINX_APACHE_PORT} ${NGINX_SSL_CERT} ${NGINX_SSL_KEY} ${NGINX_DHPARAM}' \
  < nginx/templates/nextcloud.conf.template \
  > /etc/nginx/sites-available/nextcloud

# AIO admin interface vhost (optional, recommended)
export NGINX_AIO_HOSTNAME=aio.example.com
export NGINX_AIO_PORT=8080
envsubst '${NGINX_AIO_HOSTNAME} ${NGINX_AIO_PORT} ${NGINX_SSL_CERT} ${NGINX_SSL_KEY}' \
  < nginx/templates/aio-admin.conf.template \
  > /etc/nginx/sites-available/aio-admin

ln -s /etc/nginx/sites-available/nextcloud /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/aio-admin /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

Full procedure: [docs/REVERSE_PROXY.md](docs/REVERSE_PROXY.md).

### 4 — Start

```bash
./setup.sh start
```

Then open the AIO interface (`https://127.0.0.1:8080` via an SSH tunnel, or
`https://aio.example.com` if you set up the admin vhost above), **enter your
domain**, and start Nextcloud from the AIO interface.

### 5 — Verify

```bash
curl -k https://nextcloud.example.com/status.php
# → {"installed":true, ...}
```

---

## Updating Nextcloud AIO

Updates are handled by **AIO itself** — there is no image pin to bump and no
migration to run:

1. `./setup.sh backup` (or use the AIO interface).
2. Use the AIO interface → **Stop containers** → **Start and update
   containers**.
3. The mastercontainer updates itself automatically (watchtower); AIO sends
   update notifications to Nextcloud admins.

---

## Backup & restore

AIO includes an encrypted, incremental **Borg** backup. Trigger it from the
AIO interface or with:

```bash
./setup.sh backup           # create a full encrypted backup
./setup.sh backup-check     # integrity-check existing backups
```

Restore is performed from the AIO interface (you need the encryption password
shown there). See [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

---

## Accessing the AIO admin interface

The AIO interface runs on a self-signed certificate on `AIO_INTERFACE_PORT`
(bound to `127.0.0.1` by default). Access it either:

- through an **SSH tunnel**: `ssh -L 8080:127.0.0.1:8080 user@host`, then
  open `https://127.0.0.1:8080`; or
- through your **reverse proxy** using the `aio-admin` vhost above.

---

## Multiple applications on the same host

This setup assumes the server already hosts other services behind the same
nginx. Nextcloud needs its **own dedicated domain** (it cannot run in a
subdirectory), and AIO's Apache container must be published on a free host
port (`APACHE_PORT`). Only one AIO instance per host is supported by upstream
(fixed container/volume names).

---

## TLS / HTTPS

TLS is terminated by the system nginx, **not** by AIO. Use Certbot with the
Let's Encrypt nginx plugin on the host:

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d nextcloud.example.com
```

---

## Running the test suite

Tests run entirely inside Docker against a separate nginx container that
mirrors the production proxy setup:

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml \
  run --rm --build test-runner
```

The suite covers mastercontainer startup, the AIO interface, Compose audit,
the `setup.sh` lifecycle, nginx config validation, and a privacy-leak scan.

---

## Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for:

- Domain validation failures
- Reverse-proxy debugging
- AIO interface HSTS notes
- Nextcloud Talk ports

---

## Project layout

```
nextcloud-aio/
├── VERSION                      ← this config's version (not Nextcloud's)
├── CHANGES.md                   ← changelog of this configuration wrapper
├── .env.example                 ← safe public template — copy to .env
├── docker-compose.yml           ← production stack (mastercontainer)
├── docker-compose.test.yml      ← test overlay (nginx mirror + pytest runner)
├── setup.sh                     ← bootstrap / operations / backup script
├── nginx/
│   ├── nginx.conf               ← system nginx reference configuration
│   └── templates/
│       ├── nextcloud.conf.template  ← Nextcloud vhost (envsubst)
│       └── aio-admin.conf.template  ← AIO interface vhost (envsubst)
├── .github/
│   └── copilot-instructions.md  ← agent instructions for this project
├── docs/
│   ├── ARCHITECTURE.md          ← service topology, proxy chain, ports
│   ├── ENV_VARS.md              ← complete environment-variable reference
│   ├── BACKUP_RESTORE.md        ← Borg backup & restore
│   ├── SECURITY_AUDIT.md        ← Compose security audit
│   ├── TROUBLESHOOTING.md       ← common problems
│   ├── REVERSE_PROXY.md         ← nginx reverse-proxy setup
│   ├── AGENT_CONFIGURATION.md   ← instructions/skills inventory & how-to
│   └── NETWORKING.md            ← bridge vs host network analysis
└── tests/
    ├── conftest.py              ← pytest fixtures and wait helpers
    ├── support.py               ← shared fake-docker helpers
    ├── Dockerfile.test          ← test-runner image
    ├── requirements.txt         ← Python test dependencies
    └── test_*.py                ← the test suite
```
