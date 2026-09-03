# GitHub Copilot Instructions — nextcloud-aio

## Project purpose

This repository defines and tests a **robust production Docker Compose
configuration** for the **Nextcloud AIO (All-in-One)** self-hosted
application (<https://github.com/nextcloud/all-in-one>).

The production target is a **Debian 12 / Ubuntu 24.04** server where **nginx is
already installed at the OS level** and acts as the central reverse proxy for
many applications. TLS is terminated by that nginx.

Reference docs:
- Architecture: <https://github.com/nextcloud/all-in-one#architecture-overview>
- Reverse proxy: <https://github.com/nextcloud/all-in-one/blob/main/reverse-proxy.md>
- Environment variables: <https://github.com/nextcloud/all-in-one/blob/main/compose.yaml>

---

## Language and documentation

1. **Everything in English** — code comments, README files, test descriptions,
   commit messages, and helper scripts.

---

## Change tracking

2. Update `CHANGES.md` at the root whenever files are added, modified, or
   removed during a development session. The file is used to generate commit
   messages when merging feature branches.

---

## Docker Compose rules

3. Follow the **transversal** Docker Compose conventions defined in the
   user-scope instruction file `docker-compose.instructions.md`
   (see `docs/AGENT_CONFIGURATION.md`), plus the AIO-specific rules below.
4. Use **Docker Compose v2** syntax. Never add a top-level `version:` key.
5. The Compose file defines a **single service**: the AIO mastercontainer.
   Nextcloud, Apache, PostgreSQL, Redis, … are created by the mastercontainer
   itself via the Docker socket — they are **not** defined here.
6. **Fixed upstream names (never change):**
   - `container_name: nextcloud-aio-mastercontainer`
   - volume `nextcloud_aio_mastercontainer` mounted at `/mnt/docker-aio-config`
   - auto-created network `nextcloud-aio`
7. **The mastercontainer MUST run as root.** Its entrypoint (`/start.sh`)
   exits with `Container does not run as root user. This is not supported.`
   when `EUID != 0`, and it performs root-only `groupadd`/`usermod`/`chown`/
   `chmod` on the docker socket and config volume. Never set `user:` on this
   service (see the reminder below).
8. **Never apply `cap_drop: [ALL]`** to the mastercontainer — it breaks the
   entrypoint (verified). Keep `security_opt: [no-new-privileges:true]`,
   resource limits, logging and the healthcheck.
9. Image channels only (`latest` / `beta` / `develop`) — no semantic version
   pinning. The channel is controlled by `AIO_IMAGE_TAG`.
10. Only the AIO interface port is published (loopback by default). Ports
    `80` / `8443` are **never** published — we run behind the host nginx.

## Non-root user — re-check periodically

11. **On each major AIO release, re-check whether the mastercontainer can run
    as a non-root user.** As of 2026-09-03 it cannot (explicit `EUID != 0`
    guard in `/start.sh`). To verify:

    ```bash
    docker image inspect ghcr.io/nextcloud-releases/all-in-one:latest \
      -f 'User={{.Config.User}}'
    docker run --rm --entrypoint=sh ghcr.io/nextcloud-releases/all-in-one:latest \
      -c "grep -n 'EUID' /start.sh"
    ```

    If upstream ever adds a supported non-root mode, add `user:` to the
    service and update `docs/SECURITY_AUDIT.md`.

---

## Environment variables

12. Stay **as generic as possible**: every tuneable value lives in an
    environment variable.
13. Maintain an **explicit, comprehensive `.env.example`**. Every variable
    must have a comment explaining its purpose and a safe default value.
    Never put secrets in `.env` — Nextcloud AIO generates its own secrets
    internally.

---

## Nginx reverse proxy

14. The repository ships an **nginx configuration** suitable for Debian 12 /
    Ubuntu 24.04 system nginx:
    - `nginx/templates/nextcloud.conf.template` — main Nextcloud vhost →
      `http://127.0.0.1:APACHE_PORT`.
    - `nginx/templates/aio-admin.conf.template` — AIO interface vhost →
      `https://127.0.0.1:AIO_INTERFACE_PORT` (TLS at nginx).
    - WebSocket support is always included.
15. The test environment includes an nginx container that mirrors the
    production setup; tests hit the nginx layer.

---

## Testing philosophy

16. Tests live under `tests/` and run **entirely inside Docker**.
17. Test runner: **pytest** in a dedicated `test-runner` container
    (`docker-compose.test.yml`). This is a **light** suite — it does not
    attempt a full Nextcloud bootstrap.
18. Tests must cover at least: mastercontainer startup, AIO interface
    reachability, Compose audit, `setup.sh` lifecycle, nginx config
    validation, and a privacy-leak scan.
19. Run tests with:

    ```
    docker compose -f docker-compose.yml -f docker-compose.test.yml \
      run --rm --build test-runner
    ```

---

## setup.sh

20. `setup.sh` is the user-facing entry point (`install`, `start`, `stop`,
    `restart`, `pull`, `status`, `logs`, `backup`, `backup-check`, `test`).
    It must never start containers from `install`, and must write `.env` via
    `set_env_value` (never `sed`) with input validation through
    `require_match` / `require_port`.
