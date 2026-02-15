"""
Django management command to backup all schedules to JSON files.

Usage:
    python manage.py backup_schedules
    python manage.py backup_schedules --retention-days 180
"""

import json
import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from scheduler.models import Season
from scheduler.services.schedule_data import get_schedule_data_for_season


class Command(BaseCommand):
    help = "Backup all non-deleted schedules to JSON files"

    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        retention_days = options["retention_days"]
        backup_dir = options["backup_dir"]
        
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
        
        # Get all non-deleted seasons
        seasons = Season.objects.all().order_by("id")
        
        if not seasons:
            self.stdout.write(self.style.WARNING("No seasons found to backup"))
            return
        
        backed_up_count = 0
        failed_count = 0
        
        for season in seasons:
            try:
                # Get comprehensive schedule data
                schedule_data = get_schedule_data_for_season(season)
                
                # Add backup metadata
                schedule_data["backup_metadata"] = {
                    "backup_timestamp": timestamp,
                    "season_id": season.id,
                    "season_name": season.name,
                    "is_active": season.is_active,
                    "slot_duration_minutes": season.slot_duration_minutes,
                }
                
                # Create safe filename
                safe_name = season.name.replace("/", "-").replace(" ", "_")
                filename = f"season-{season.id}_{safe_name}.json"
                filepath = os.path.join(backup_path, filename)
                
                # Write JSON file
                with open(filepath, "w") as f:
                    json.dump(schedule_data, f, indent=2)
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Backed up: {season.name} -> {filename}")
                )
                backed_up_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to backup {season.name}: {e}")
                )
                failed_count += 1
        
        # Clean up old backups based on retention policy
        self.cleanup_old_backups(backup_dir, retention_days)
        
        # Summary
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Backup complete: {backed_up_count} seasons backed up to {backup_path}"
            )
        )
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f"{failed_count} seasons failed"))

    def cleanup_old_backups(self, backup_dir, retention_days):
        """Remove backup directories older than retention_days."""
        if not os.path.exists(backup_dir):
            return
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        try:
            for entry in os.listdir(backup_dir):
                entry_path = os.path.join(backup_dir, entry)
                
                # Only process directories that look like timestamps
                if not os.path.isdir(entry_path):
                    continue
                
                # Parse directory name as timestamp
                try:
                    dir_date = datetime.strptime(entry, "%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    # Not a backup directory, skip
                    continue
                
                # Delete if older than retention period
                if dir_date < cutoff_date:
                    import shutil
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
