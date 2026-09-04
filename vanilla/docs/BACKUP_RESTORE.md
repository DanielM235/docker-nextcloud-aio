# Backup & Restore (vanilla)

Unlike AIO, this stack has no built-in backup UI. `./setup.sh backup` performs
a **full instance backup**:

- **Database** — `mariadb-dump` (single transaction).
- **Data directory** — the `NEXTCLOUD_DATA_DIR` host path (external disk),
  archived with `tar`.
- **Config / app volume** — the `nextcloud` named volume
  (`config.php`, `custom_apps`, themes), archived with `tar`.
- **`.env`** — copied alongside (contains the DB credentials).

## Create a backup

```bash
./setup.sh backup
```

Backups land in `BACKUP_DIR/<timestamp>/` with a `manifest.txt`. Run it from
cron for unattended backups, e.g.:

```cron
30 3 * * *  cd /path/to/vanilla && ./setup.sh backup
```

## Restore

```bash
./setup.sh restore backups/<timestamp>
```

`restore` puts Nextcloud into maintenance mode, restores the DB, data and
config, then leaves maintenance mode. After a restore on a fresh host, run
`./setup.sh start` and re-check `NEXTCLOUD_DATA_DIR`.

## Notes

- Backups are **not encrypted** — store them on encrypted storage or pipe them
  through your preferred encryption tool.
- The DB dump is taken with `--single-transaction`, consistent for InnoDB
  (default in MariaDB 11.4).
- Exclude nothing by default; if your data directory is very large, consider a
  dedicated disk-level snapshot instead of `tar`.
