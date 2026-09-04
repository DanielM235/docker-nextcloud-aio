# Updating Nextcloud (vanilla)

The Nextcloud image performs its own database migration when it starts with a
newer version and the persisted `/var/www/html` volume. Because it can only
upgrade **one major version at a time**, never jump majors.

## 1 — Find the latest version

```bash
# Latest GitHub release tag
curl -s https://api.github.com/repos/nextcloud/server/releases/latest | grep '"tag_name"'
# Or list Docker Hub tags
curl -s "https://hub.docker.com/v2/repositories/library/nextcloud/tags?page_size=25&name=apache" | grep '"name"'
```

The Docker tag is `<major>.<minor>.<patch>-apache`, e.g. `34.0.3-apache`.

## 2 — Back up first

```bash
./setup.sh backup
```

## 3 — Bump the pinned tag

Edit `NEXTCLOUD_IMAGE_TAG` in `.env` (and the default in `.env.example`).

## 4 — Update

```bash
./setup.sh update
```

`update` pulls the new image and recreates the containers; Nextcloud runs its
migration on startup. Watch the logs:

```bash
./setup.sh logs app
```

## 5 — Post-update checks

```bash
./setup.sh occ status
./setup.sh occ app:list
./setup.sh occ maintenance:repair
```

## Rules

- **One major at a time** — e.g. `34.x → 35.x`, not `34.x → 36.x`.
- Keep MariaDB (`11.4` LTS) and Redis updated independently (security patches)
  by bumping their tags and re-running `./setup.sh update`.
- Record the change in `../CHANGES.md` and the config `VERSION`.
