"""
Django management command to restore the database from a backup.

- SQLite (dev): copies the backup file over db.sqlite3
- Postgres (prod): runs psql to restore a .sql dump

WARNING: This replaces the ENTIRE database, including auth/admin data.

Usage:
    python manage.py restore_schedule backups/2026-02-15_02-00-00/db.sqlite3
    python manage.py restore_schedule backups/2026-02-15_02-00-00/db_dump.sql --yes
"""

import os
import shutil
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore the database from a backup file (replaces entire DB)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "backup_file",
            type=str,
            help="Path to the backup file (.sqlite3 or .sql)",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options) -> None:
        backup_file: str = options["backup_file"]
        skip_confirm: bool = options["yes"]

        if not os.path.exists(backup_file):
            raise CommandError(f"Backup file not found: {backup_file}")

        db_settings = settings.DATABASES["default"]
        engine: str = db_settings["ENGINE"]

        # Determine expected file type
        if "sqlite3" in engine:
            if not backup_file.endswith(".sqlite3"):
                raise CommandError(
                    f"Expected a .sqlite3 file for SQLite restore, got: {backup_file}"
                )
        elif "postgresql" in engine or "postgis" in engine:
            if not backup_file.endswith(".sql"):
                raise CommandError(
                    f"Expected a .sql file for Postgres restore, got: {backup_file}"
                )
        else:
            raise CommandError(f"Unsupported database engine: {engine}")

        # Confirm with user
        if not skip_confirm:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: This will replace the ENTIRE database, "
                    "including all user accounts, sessions, and admin data."
                )
            )
            self.stdout.write(f"Restore from: {backup_file}")
            response = input("Type 'yes' to confirm: ")
            if response.strip().lower() != "yes":
                self.stdout.write("Restore cancelled.")
                return

        if "sqlite3" in engine:
            self._restore_sqlite(db_settings, backup_file)
        else:
            self._restore_postgres(db_settings, backup_file)

    def _restore_sqlite(self, db_settings: dict, backup_file: str) -> None:
        """Restore SQLite by copying the backup file over the database."""
        db_path: str = str(db_settings["NAME"])

        shutil.copy2(backup_file, db_path)

        size_kb = os.path.getsize(db_path) / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Database restored from {backup_file} ({size_kb:.0f} KB)"
            )
        )

    def _restore_postgres(self, db_settings: dict, backup_file: str) -> None:
        """Restore Postgres using psql."""
        env = os.environ.copy()
        password = db_settings.get("PASSWORD", "")
        if password:
            env["PGPASSWORD"] = password

        cmd = [
            "psql",
            "-h", db_settings.get("HOST", "localhost"),
            "-p", str(db_settings.get("PORT", "5432")),
            "-U", db_settings.get("USER", "postgres"),
            "-d", db_settings["NAME"],
            "-f", backup_file,
        ]

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                self.stdout.write(
                    self.style.ERROR(f"psql restore failed: {result.stderr}")
                )
                return
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    "psql not found. Make sure PostgreSQL client tools are installed."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"Database restored from {backup_file}")
        )
