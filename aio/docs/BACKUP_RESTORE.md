# Backup & Restore

Nextcloud AIO ships a built-in backup solution based on
[BorgBackup](https://www.borgbackup.org/). Backups are incremental,
compressed and **encrypted**. They act as a full-instance restore point
(database + files + mastercontainer configuration).

## Create a backup

From the AIO interface:

1. Open the AIO interface → **Backup and restore**.
2. Choose a backup location (a host path such as an external drive, or a
   remote Borg repository).
3. Click **Create Backup**.

Or from the shell (uses whatever backup location is configured in the
interface):

```bash
./setup.sh backup
```

This runs the mastercontainer's internal backup trigger.

> **Save the encryption password** shown in the AIO interface. Without it you
> cannot restore.

## Verify backups

```bash
./setup.sh backup-check
```

Results appear in the `nextcloud-aio-borgbackup` container logs.

## Restore

1. Start a fresh AIO instance (or use an existing one with stopped
   containers).
2. Open the AIO interface → **Restore former AIO instance from backup**.
3. Enter the backup location and encryption password.
4. Select the backup and click **Restore selected backup**.

## Notes

- Files mounted via Nextcloud **external storage** are **not** backed up — add
  extra Docker volumes/host paths in the AIO interface if needed.
- To exclude the data directory (or preview folder) from backups, create a
  `.noaiobackup` file in that directory (only recommended with an external
  backup of the data directory).
- See the official docs for remote Borg repositories and retention policy
  tuning (`BORG_RETENTION_POLICY` in `.env`).
