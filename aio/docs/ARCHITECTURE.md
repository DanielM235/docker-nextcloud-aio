# Architecture

This document describes the service topology, the reverse-proxy chain and the
port layout of this Nextcloud AIO deployment.

## How Nextcloud AIO works

Nextcloud AIO is orchestrated by a single **mastercontainer**
(`ghcr.io/nextcloud-releases/all-in-one`). The mastercontainer:

1. Runs the **AIO web interface** (HTTPS, self-signed certificate) on its
   internal port `8080`.
2. Mounts the host Docker socket **read-only** and uses it to create, update
   and manage all the *sibling* containers:

   | Sibling container | Purpose |
   |-------------------|---------|
   | `nextcloud-aio-nextcloud` | Nextcloud application (PHP-FPM) |
   | `nextcloud-aio-apache` | Apache reverse proxy in front of Nextcloud |
   | `nextcloud-aio-database` | PostgreSQL |
   | `nextcloud-aio-redis` | Redis (cache + file locking) |
   | `nextcloud-aio-notify-push` | High-performance push notifications |
   | … plus optional ones (Talk, Nextcloud Office, ClamAV, …) | enabled via the interface |

   Siblings live on an automatically created Docker network named
   `nextcloud-aio`. They are **not** defined in this repository's Compose file
   — the mastercontainer manages them.

## Reverse-proxy chain

```
Browser
   │  https://nextcloud.example.com
   ▼
System nginx (host, TLS termination)
   │  proxy_pass → http://127.0.0.1:APACHE_PORT  (default 11000)
   ▼
nextcloud-aio-apache  (published by AIO on APACHE_PORT)
   │
   ▼
nextcloud-aio-nextcloud
```

The AIO admin interface is exposed separately, on its own hostname, still
through the host nginx:

```
Browser
   │  https://aio.example.com
   ▼
System nginx (host, TLS termination)
   │  proxy_pass → https://127.0.0.1:AIO_INTERFACE_PORT  (proxy_ssl_verify off)
   ▼
nextcloud-aio-mastercontainer :8080  (self-signed)
```

## Ports

| Port | Where | Purpose | Published? |
|------|-------|---------|-----------|
| `APACHE_PORT` (11000) | host | AIO Apache container; nginx proxies to it | yes (bound per `APACHE_IP_BINDING`) |
| `AIO_INTERFACE_PORT` (8080) | host | AIO web interface (self-signed) | yes (bound per `AIO_INTERFACE_BIND_HOST`) |
| `80`, `8443` | host | AIO built-in HTTPS / ACME | **no** — behind our reverse proxy |
| `TALK_PORT` (3478 TCP+UDP) | host | Nextcloud Talk TURN | only if Talk enabled |

## Networks

- The **mastercontainer** runs on the default `bridge` network (as upstream
  ships it).
- The **siblings** run on the auto-created `nextcloud-aio` network.
- This repository's Compose project uses `name:` (from `COMPOSE_PROJECT_NAME`)
  only for the Compose project itself; it does not affect AIO's fixed names.

## Fixed names (upstream constraints)

The following **cannot** be changed, or AIO's self-update and built-in backup
break:

- `container_name: nextcloud-aio-mastercontainer`
- volume `nextcloud_aio_mastercontainer` mounted at `/mnt/docker-aio-config`
- network `nextcloud-aio` (created by the mastercontainer)

See [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for the implications.
