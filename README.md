# nextcloud-docker

**Production Docker Compose configurations for self-hosted Nextcloud**, for a
**Debian 12 / Ubuntu 24.04** server where **nginx is already installed at the
OS level** and terminates TLS for many applications.

Two configurations are provided — pick one:

| | **AIO** (`aio/`) | **Vanilla** (`vanilla/`) |
|---|---|---|
| Basis | `nextcloud/all-in-one` (single mastercontainer) | Official `nextcloud` image + MariaDB + Redis |
| Docker socket | Yes (read-only) — the mastercontainer orchestrates everything | **No** |
| Services you manage | 1 (the rest is auto-created) | `db`, `redis`, `app`, `cron` |
| Upgrades | By AIO itself (interface / watchtower) | `./setup.sh update`, one major at a time |
| Backup | Built-in Borg (UI + script trigger) | `./setup.sh backup` (mysqldump + data + config) |
| Hardening | `no-new-privileges`, resource limits; orchestrator stays root | `cap_drop: ALL`, non-root services |
| Best for | Ease of maintenance, full Hub feature set | Full control, no socket access, host-level backups |

## Choose

- **AIO** → see [`aio/README.md`](aio/README.md).
- **Vanilla** → see [`vanilla/README.md`](vanilla/README.md).

## Host hardening (applies to both)

Follow [`docs/HOST_SECURITY.md`](docs/HOST_SECURITY.md) for the firewall
(nftables), fail2ban, SSH and TLS guidance that applies regardless of the
configuration you choose.

## Agent configuration

[`docs/AGENT_CONFIGURATION.md`](docs/AGENT_CONFIGURATION.md) explains how the
coding assistant discovers instructions/skills for these Docker Compose
projects, and how to extend them.

## Layout

```
.
├── aio/            ← Nextcloud AIO configuration (self-contained)
├── vanilla/        ← vanilla Nextcloud configuration (self-contained)
├── docs/           ← shared docs (host security, agent configuration)
├── .github/        ← Copilot instructions for this repository
├── README.md       ← this file
├── CHANGES.md
└── .gitignore
```
