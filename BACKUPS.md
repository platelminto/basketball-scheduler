# Database Backups

Simple raw database dumps — no custom serialization, just copy the database.

## How It Works

- **Dev (SQLite)**: Copies `db.sqlite3` into a timestamped backup directory
- **Prod (Postgres)**: Runs `pg_dump` to create a `.sql` dump file

## Automatic Backups

Set up a cron job to run backups weekly:

```bash
# Add to crontab (crontab -e)
0 2 * * 2 cd /path/to/basketball-scheduler && uv run python manage.py backup_schedules
```

### Docker

The `web` container has `./backups:/app/backups` mounted, so backups persist on the host. Use a cron container or host cron:

```bash
# Host cron example
0 2 * * 2 docker compose exec web uv run python manage.py backup_schedules
```

## Manual Backup

```bash
python manage.py backup_schedules
```

Options:
- `--retention-days N` — Keep backups for N days (default: 365)
- `--backup-dir PATH` — Custom backup directory (default: `backups/`)

## Restore

**WARNING**: Restore replaces the **entire database**, including user accounts, sessions, and admin data.

```bash
# SQLite (dev)
python manage.py restore_schedule backups/2026-02-15_02-00-00/db.sqlite3

# Postgres (prod)
python manage.py restore_schedule backups/2026-02-15_02-00-00/db_dump.sql

# Skip confirmation prompt
python manage.py restore_schedule backups/2026-02-15_02-00-00/db.sqlite3 --yes
```

## Backup Structure

```
backups/
├── 2026-02-11_02-00-00/
│   └── db.sqlite3          # or db_dump.sql for Postgres
├── 2026-02-18_02-00-00/
│   └── db.sqlite3
└── ...
```

## Retention Policy

Backups older than 365 days (configurable via `--retention-days`) are automatically deleted during each backup run.
