"""
Django management command to restore a schedule from a backup JSON file.

Usage:
    python manage.py restore_schedule /path/to/backup/season-1_24-25-Season-1.json
    python manage.py restore_schedule /path/to/backup/season-1_24-25-Season-1.json --overwrite
"""

import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from scheduler.models import Season, Level, SeasonTeam, TeamOrganization, Week, OffWeek, Game
from datetime import datetime


class Command(BaseCommand):
    help = "Restore a schedule from a backup JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            type=str,
            help="Path to the backup JSON file",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing season if it exists (will delete existing data)",
        )
        parser.add_argument(
            "--rename",
            type=str,
            default=None,
            help="Rename the restored season (e.g., '24/25 Season 1 (Restored)')",
        )

    def handle(self, *args, **options):
        backup_file = options["backup_file"]
        overwrite = options["overwrite"]
        rename = options["rename"]
        
        # Validate backup file
        if not os.path.exists(backup_file):
            raise CommandError(f"Backup file not found: {backup_file}")
        
        # Load backup data
        try:
            with open(backup_file, "r") as f:
                backup_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON file: {e}")
        except Exception as e:
            raise CommandError(f"Failed to read backup file: {e}")
        
        # Validate backup structure
        if "season" not in backup_data or "weeks" not in backup_data:
            raise CommandError("Invalid backup format: missing required fields")
        
        season_data = backup_data["season"]
        backup_metadata = backup_data.get("backup_metadata", {})
        
        original_season_name = season_data["name"]
        season_name = rename if rename else original_season_name
        
        # Check if season already exists
        existing_season = Season.objects.filter(name=season_name).first()
        
        if existing_season and not overwrite:
            raise CommandError(
                f"Season '{season_name}' already exists. Use --overwrite to replace it "
                f"or --rename 'New Name' to restore with a different name."
            )
        
        self.stdout.write(f"Restoring season: {season_name}")
        if backup_metadata:
            backup_time = backup_metadata.get("backup_timestamp", "unknown")
            self.stdout.write(f"Backup from: {backup_time}")
        
        # Perform restoration in a transaction
        try:
            with transaction.atomic():
                # Delete existing season if overwriting
                if existing_season and overwrite:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Deleting existing season '{season_name}'..."
                        )
                    )
                    existing_season.delete()
                
                # Restore the season
                restored_season = self._restore_season(
                    season_name, backup_data, backup_metadata
                )
                
                self.stdout.write("")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Successfully restored season: {restored_season.name} (ID: {restored_season.id})"
                    )
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Restore failed: {e}"))
            raise

    def _restore_season(self, season_name, backup_data, backup_metadata):
        """Restore a season from backup data."""
        season_data = backup_data["season"]
        
        # Create season
        slot_duration = backup_metadata.get("slot_duration_minutes", 70)
        season = Season.objects.create(
            name=season_name,
            slot_duration_minutes=slot_duration,
            is_active=False,  # Don't activate by default
        )
        self.stdout.write(f"Created season: {season.name}")
        
        # Restore levels
        levels_map = {}
        for level_data in backup_data.get("levels", []):
            level = Level.objects.create(
                season=season,
                name=level_data["name"],
                display_order=level_data.get("display_order", 0),
            )
            levels_map[level_data["id"]] = level
            self.stdout.write(f"  Created level: {level.name}")
        
        # Restore teams (create or link TeamOrganizations, then create SeasonTeams)
        season_teams_map = {}
        teams_by_level = backup_data.get("teams_by_level", {})
        
        for level_id_str, teams in teams_by_level.items():
            level_id = int(level_id_str)
            if level_id not in levels_map:
                continue
            
            level = levels_map[level_id]
            
            for team_data in teams:
                team_name = team_data["name"]
                
                # Get or create TeamOrganization
                # First, try to find an existing non-deleted team
                existing_teams = TeamOrganization.objects.filter(name=team_name)
                
                if existing_teams.exists():
                    # If multiple teams exist, prefer non-archived ones
                    team_org = existing_teams.filter(is_archived=False).first()
                    if not team_org:
                        # All are archived, just use the first one
                        team_org = existing_teams.first()
                    created = False
                else:
                    # Create new team
                    team_org = TeamOrganization.objects.create(name=team_name)
                    created = True
                
                # Create SeasonTeam
                season_team = SeasonTeam.objects.create(
                    season=season,
                    team=team_org,
                    level=level,
                )
                
                # Map old season_team_id to new season_team
                old_season_team_id = team_data.get("season_team_id") or team_data.get("id")
                if old_season_team_id:
                    season_teams_map[old_season_team_id] = season_team
                
                action = "Created" if created else "Linked"
                self.stdout.write(f"  {action} team: {team_name} in {level.name}")
        
        # Restore weeks
        weeks_map = {}
        weeks_data = backup_data.get("weeks", {})
        
        for week_num_str, week_data in weeks_data.items():
            monday_date = datetime.strptime(
                week_data["monday_date"], "%Y-%m-%d"
            ).date()
            
            if week_data.get("isOffWeek"):
                # Create OffWeek
                off_week = OffWeek.objects.create(
                    season=season,
                    monday_date=monday_date,
                    title=week_data.get("title", "Off Week"),
                    description=week_data.get("description", ""),
                    has_basketball=week_data.get("has_basketball", False),
                    start_time=self._parse_time(week_data.get("start_time")),
                    end_time=self._parse_time(week_data.get("end_time")),
                )
                self.stdout.write(
                    f"  Created off week: {monday_date} - {off_week.title}"
                )
            else:
                # Create regular Week
                week = Week.objects.create(
                    season=season,
                    week_number=week_data["week_number"],
                    monday_date=monday_date,
                )
                weeks_map[week_data["week_number"]] = week
                self.stdout.write(f"  Created week {week.week_number}: {monday_date}")
        
        # Restore games
        games_count = 0
        for week_num_str, week_data in weeks_data.items():
            if week_data.get("isOffWeek"):
                continue
            
            week_number = week_data["week_number"]
            if week_number not in weeks_map:
                continue
            
            week = weeks_map[week_number]
            
            for game_data in week_data.get("games", []):
                try:
                    # Get level
                    level_id = game_data.get("level_id")
                    level = levels_map.get(level_id)
                    if not level:
                        continue
                    
                    # Get teams
                    team1_id = game_data.get("season_team1_id") or game_data.get("team1_id")
                    team2_id = game_data.get("season_team2_id") or game_data.get("team2_id")
                    
                    season_team1 = season_teams_map.get(team1_id)
                    season_team2 = season_teams_map.get(team2_id)
                    
                    if not season_team1 or not season_team2:
                        continue
                    
                    # Get referee
                    referee_id = game_data.get("referee_season_team_id") or game_data.get("referee_team_id")
                    referee_season_team = season_teams_map.get(referee_id) if referee_id else None
                    referee_name = game_data.get("referee_name")
                    
                    # Create game
                    Game.objects.create(
                        level=level,
                        week=week,
                        season_team1=season_team1,
                        season_team2=season_team2,
                        referee_season_team=referee_season_team,
                        referee_name=referee_name,
                        day_of_week=game_data.get("day_of_week"),
                        time=self._parse_time(game_data.get("time")),
                        court=game_data.get("court"),
                        team1_score=game_data.get("team1_score"),
                        team2_score=game_data.get("team2_score"),
                    )
                    games_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"  Skipped game: {e}")
                    )
        
        self.stdout.write(f"  Created {games_count} games")
        
        return season

    def _parse_time(self, time_str):
        """Parse time string to time object."""
        if not time_str:
            return None
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except (ValueError, TypeError):
            return None
