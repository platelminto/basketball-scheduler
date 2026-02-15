# Schedule Backups

This directory contains automated backups of all basketball schedules.

## Automatic Backups

Backups are created automatically every Tuesday at 2:00 AM via cron.

### Setting up Automated Backups

Add this line to your crontab:

```bash
0 2 * * 2 cd /path/to/basketball-scheduler && uv run python manage.py backup_schedules
```

To edit crontab:
```bash
crontab -e
```

### Docker Setup

For Docker deployments, add to docker-compose.yml or use a cron container:

```yaml
services:
  backup:
    image: your-app-image
    volumes:
      - ./backups:/app/backups
    command: >
      sh -c "echo '0 2 * * 2 cd /app && uv run python manage.py backup_schedules' | crontab - && crond -f"
```

## Manual Backups

Run a backup manually anytime:

```bash
python manage.py backup_schedules
```

Options:
- `--retention-days N`: Keep backups for N days (default: 365)
- `--backup-dir PATH`: Custom backup directory location

## Restore from Backup

To restore a schedule from a backup:

```bash
# Restore as a new season
python manage.py restore_schedule backups/2026-02-15_02-00-00/season-1_24-25-Season-1.json

# Restore with a new name
python manage.py restore_schedule backups/2026-02-15_02-00-00/season-1_24-25-Season-1.json --rename "24/25 Season 1 (Restored)"

# Overwrite existing season (destructive!)
python manage.py restore_schedule backups/2026-02-15_02-00-00/season-1_24-25-Season-1.json --overwrite
```

## Backup Structure

```
backups/
├── 2026-02-11_02-00-00/
│   ├── season-1_24-25-Season-1.json
│   └── season-2_24-25-Season-2.json
├── 2026-02-18_02-00-00/
│   ├── season-1_24-25-Season-1.json
│   └── season-3_24-25-Season-3.json
└── README.md
```

Each backup includes:
- Complete season metadata (name, slot duration, teams, levels)
- All games with scores, referees, and scheduling
- Week dates and off-week information
- Timestamp and season identifiers

## Retention Policy

By default, backups older than 365 days are automatically deleted during each backup run. This keeps the backup directory from growing indefinitely while maintaining a full year of history.

Backup files are small (typically a few KB per season), so storage requirements are minimal.
