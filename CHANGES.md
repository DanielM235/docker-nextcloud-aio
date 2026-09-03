# Changelog — nextcloud-aio

All notable changes to this configuration wrapper are documented here.
This file is used to generate commit messages when merging feature branches.

## [1.0.0] — 2026-09-03

### Added
- Initial production Docker Compose configuration for Nextcloud AIO.
- Hardened `docker-compose.yml` (single mastercontainer service).
- `.env.example` with every tunable documented and generic defaults.
- Host nginx reverse-proxy templates: Nextcloud vhost + AIO admin interface.
- `setup.sh` bootstrap / operation / backup script.
- Documentation: architecture, environment variables, backup & restore,
  security audit, troubleshooting, reverse proxy.
- Light CI test suite: startup, compose audit, setup.sh lifecycle, nginx
  config validation, privacy-leak scan.
- `.github/copilot-instructions.md` — project conventions + a periodic
  non-root re-check reminder.
- `docs/AGENT_CONFIGURATION.md` — inventory of instruction/skill scopes and
  how to extend them.
- `docs/NETWORKING.md` — bridge vs host networking analysis.
- `docs/SECURITY_AUDIT.md` — documented the verified "mastercontainer
  requires root" finding.
