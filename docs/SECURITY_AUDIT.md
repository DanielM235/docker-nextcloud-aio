# Security Audit

This document records the security posture of `docker-compose.yml`, what is
hardened, and — importantly — what **cannot** be hardened and why.

## Hardening applied to the mastercontainer

| Measure | Value | Rationale |
|---------|-------|-----------|
| `security_opt: no-new-privileges:true` | on | Prevent privilege escalation via setuid binaries. |
| `deploy.resources.limits` | CPU + memory + pids | Bound runaway resource usage. |
| `logging` | `max-size` + `max-file` | Prevent unbounded log growth. |
| `healthcheck` | HTTPS probe of the interface | Detect a wedged mastercontainer. |
| `ports` | loopback-bound | The AIO interface is bound to `127.0.0.1` by default. |
| docker socket | read-only mount | The mastercontainer can only read the socket. |

> **Why no `cap_drop: [ALL]`** — the mastercontainer's entrypoint fixes the
> docker.sock permissions and chowns its directories on first boot. Dropping
> `DAC_OVERRIDE` breaks these steps (verified against the actual image: the
> container crash-loops with `Permission denied`). It is a privileged
> orchestrator by design, so it keeps the default Linux capability set. This is
> the same trust model as running Portainer or Watchtower.


## Non-root user — not supported (verified)

The mastercontainer **cannot run as a non-root user**. Verified against
`ghcr.io/nextcloud-releases/all-in-one:latest` (2026-09-03):

- Image default: `User=root` (no `USER` instruction in the image).
- `/start.sh` (the entrypoint) contains an explicit guard:

  ```bash
  if [ "$EUID" != "0" ]; then
      print_red "Container does not run as root user. This is not supported."
      exit 1
  fi
  ```

- It performs root-only operations at startup: `groupadd`/`usermod` to fix the
  docker socket group, and `chown`/`chmod` on `/mnt/docker-aio-config`,
  `/root` and `/tmp/twig-cache`. The web UI itself is dropped to `www-data`
  (uid 33) internally via `su-exec`.

**Re-check periodically** (on each major AIO release) whether upstream adds a
supported non-root mode:

```bash
docker image inspect ghcr.io/nextcloud-releases/all-in-one:latest -f 'User={{.Config.User}}'
docker run --rm --entrypoint=sh ghcr.io/nextcloud-releases/all-in-one:latest \
  -c "grep -n 'EUID' /start.sh"
```

If it ever does, add `user:` to the service here and update this document.


## What is deliberately NOT hardened (and why)

1. **Fixed names** — `container_name: nextcloud-aio-mastercontainer` and the
   volume `nextcloud_aio_mastercontainer` are required by upstream; the
   self-update and built-in backup rely on them. They cannot be namespaced
   per instance.

2. **Rolling image tag** — AIO ships channels (`latest`/`beta`/`develop`), not
   immutable semantic versions. The channel choice is the version control
   mechanism; updates are performed by AIO itself.

3. **Docker socket access** — the mastercontainer *is* the orchestrator. It
   needs read access to the socket to create and manage the sibling
   containers. It runs as root inside the container. This is by design (the
   same model as Portainer). If you cannot accept socket access, use the
   upstream [manual-install](https://github.com/nextcloud/all-in-one/tree/main/manual-install)
   approach instead.

4. **Sibling containers** — the Nextcloud/Apache/PostgreSQL/Redis containers
   are created by the mastercontainer, not by this Compose file, so their
   security options are controlled by AIO (which already runs many of them
   non-root with read-only root filesystems).

5. **`read_only: true`** — not applied to the mastercontainer because it writes
   to `/mnt/docker-aio-config` and runtime directories.

## Secrets

- No secrets live in `.env` or `docker-compose.yml`. Nextcloud AIO generates
  its own passwords internally during setup and stores them in the
  `nextcloud_aio_mastercontainer` volume.
- `.env` is git-ignored; `.env.example` contains only generic defaults.

## Recommendations

- Keep the AIO interface bound to `127.0.0.1` and access it via an SSH tunnel
  or your TLS reverse proxy.
- Only expose `APACHE_PORT` to the interface nginx connects to
  (`APACHE_IP_BINDING=127.0.0.1` when nginx is on the same host).
- If you enable Nextcloud Talk, restrict `TALK_PORT` (TCP+UDP) at the
  firewall.
- Use the built-in backup (encrypted) and store the encryption password
  safely.
