# Security posture (vanilla)

This configuration favours security while keeping full Nextcloud functionality.

## Container hardening

| Measure | db | redis | app | cron |
|---------|----|-------|-----|------|
| Non-root process | `user: mysql` | `user: redis` | PHP runs as `www-data` (image default) | `user: www-data` |
| `cap_drop: ALL` | ✓ | ✓ | — (default caps) | ✓ |
| `no-new-privileges:true` | ✓ | ✓ | ✓ | ✓ |
| Docker socket mounted | — | — | **no** | — |
| Host ports | none | none | `127.0.0.1:APP_HTTP_PORT` only | none |
| Resource limits | ✓ | ✓ | ✓ | ✓ |
| Log rotation | ✓ | ✓ | ✓ | ✓ |
| Healthcheck | ✓ | ✓ | ✓ | — |

Redis is additionally protected with `requirepass` (`REDIS_HOST_PASSWORD`):
even a process that reaches the internal Docker network cannot read or write
the cache without the password. Nextcloud receives the same password through
its `REDIS_HOST_PASSWORD` environment variable.

## Why the `app` container keeps default capabilities

The official image's entrypoint runs as root on first boot to **rsync** the
Nextcloud source into `/var/www/html` and `chown` the volumes, then drops to
`www-data` for Apache. A full `cap_drop: [ALL]` breaks that rsync step
(verified: `rename`/`unlink` fail with `Operation not permitted`). We
therefore keep the default capability set for `app` only, while still applying
`no-new-privileges:true`, resource limits and **no** `--privileged`. `cron`
runs `/cron.sh` as `www-data` and keeps `cap_drop: [ALL]`.

## What is deliberately avoided

- **No Docker socket** in any container — Docker is managed only from the host
  CLI.
- **No published ports** except the app's loopback port (nginx is the only
  entry point).
- **No `host` network mode** — all services stay on the internal bridge
  network, NAT-isolated from the host.

## Host hardening

Firewall (nftables), fail2ban, SSH and TLS guidance live in
[../docs/HOST_SECURITY.md](../docs/HOST_SECURITY.md). Recommended Nextcloud
hardening settings (HSTS via nginx, `allowed_admin_ranges`, trusted domains)
are applied via the nginx template and `.env` where applicable.
