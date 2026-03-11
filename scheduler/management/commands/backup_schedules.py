"""
Django management command to backup the database.

- SQLite (dev): copies the db.sqlite3 file
- Postgres (prod): runs pg_dump to create a .sql dump

Usage:
    python manage.py backup_schedules
    python manage.py backup_schedules --retention-days 180
    python manage.py backup_schedules --backup-dir /custom/path
"""

import os
import shutil
import subprocess
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backup the database (SQLite file copy or Postgres pg_dump)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--retention-days",
            type=int,
            default=365,
            help="Number of days to retain old backups (default: 365)",
        )
        parser.add_argument(
            "--backup-dir",
            type=str,
            default=None,
            help="Custom backup directory path (default: backups/)",
        )

    def handle(self, *args, **options) -> None:
        retention_days: int = options["retention_days"]
        backup_dir: str | None = options["backup_dir"]

        if backup_dir is None:
            backup_dir = os.path.join(settings.BASE_DIR, "backups")

        # Create timestamped backup directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = os.path.join(backup_dir, timestamp)

        try:
            os.makedirs(backup_path, exist_ok=True)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to create backup directory: {e}")
            )
            return

        db_settings = settings.DATABASES["default"]
        engine: str = db_settings["ENGINE"]

        if "sqlite3" in engine:
            self._backup_sqlite(db_settings, backup_path)
        elif "postgresql" in engine or "postgis" in engine:
            self._backup_postgres(db_settings, backup_path)
        else:
            self.stdout.write(
                self.style.ERROR(f"Unsupported database engine: {engine}")
            )
            return

        # Clean up old backups based on retention policy
        self._cleanup_old_backups(backup_dir, retention_days)

    def _backup_sqlite(self, db_settings: dict, backup_path: str) -> None:
        """Backup SQLite by copying the database file."""
        db_path: str = str(db_settings["NAME"])

        if not os.path.exists(db_path):
            self.stdout.write(
                self.style.ERROR(f"SQLite database not found: {db_path}")
            )
            return

        dest = os.path.join(backup_path, "db.sqlite3")
        shutil.copy2(db_path, dest)

        size_kb = os.path.getsize(dest) / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Backup complete: {dest} ({size_kb:.0f} KB)"
            )
        )

    def _backup_postgres(self, db_settings: dict, backup_path: str) -> None:
        """Backup Postgres using pg_dump."""
        dest = os.path.join(backup_path, "db_dump.sql")

        env = os.environ.copy()
        password = db_settings.get("PASSWORD", "")
        if password:
            env["PGPASSWORD"] = password

        cmd = [
            "pg_dump",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "-h", db_settings.get("HOST", "localhost"),
            "-p", str(db_settings.get("PORT", "5432")),
            "-U", db_settings.get("USER", "postgres"),
            "-d", db_settings["NAME"],
            "-f", dest,
        ]

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                self.stdout.write(
                    self.style.ERROR(f"pg_dump failed: {result.stderr}")
                )
                return
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    "pg_dump not found. Make sure PostgreSQL client tools are installed."
                )
            )
            return

        size_kb = os.path.getsize(dest) / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Backup complete: {dest} ({size_kb:.0f} KB)"
            )
        )

    def _cleanup_old_backups(self, backup_dir: str, retention_days: int) -> None:
        """Remove backup directories older than retention_days."""
        if not os.path.exists(backup_dir):
            return

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        try:
            for entry in os.listdir(backup_dir):
                entry_path = os.path.join(backup_dir, entry)

                if not os.path.isdir(entry_path):
                    continue

                try:
                    dir_date = datetime.strptime(entry, "%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    continue

                if dir_date < cutoff_date:
                    shutil.rmtree(entry_path)
                    deleted_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"Cleaned up old backup: {entry}")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during cleanup: {e}")
            )

        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Cleaned up {deleted_count} old backup(s)")
            )
