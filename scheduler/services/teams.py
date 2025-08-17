"""
Team and level management service functions.

This module contains business logic for managing teams and levels
including creation, updates, and safe deletion operations.
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from scheduler.models import Season, Level, Team, Game


def handle_team_deletions(existing_teams_by_id, processed_team_ids):
    """Safely delete teams that are no longer present."""
    teams_to_remove = set(existing_teams_by_id.keys()) - processed_team_ids
    for team_id in teams_to_remove:
        team = existing_teams_by_id[team_id]
        # Check if team has any games
        if Game.objects.filter(
            Q(team1=team) | Q(team2=team) | Q(referee_team=team)
        ).exists():
            # Team has games, so we can't delete it
            pass  # Keep the team
        else:
            # Safe to delete since no games reference it
            team.delete()


def handle_team_deletions_old_format(existing_teams, updated_teams):
    """Safely delete teams using old format (name-based)."""
    teams_to_remove = set(existing_teams.keys()) - updated_teams
    for team_name in teams_to_remove:
        team = existing_teams[team_name]
        if Game.objects.filter(
            Q(team1=team) | Q(team2=team) | Q(referee_team=team)
        ).exists():
            pass  # Keep the team
        else:
            team.delete()


def process_level_updates(levels_data, existing_levels_by_id, existing_levels_by_name, season):
    """Process level updates using new format with IDs."""
    processed_level_ids = set()

    for level_info in levels_data:
        level_id = level_info.get("id")
        level_name = level_info.get("name", "").strip()
        team_infos = level_info.get("teams", [])

        if not level_name:
            continue

        # Check if this is a rename or update of existing level
        if level_id and level_id in existing_levels_by_id:
            level = existing_levels_by_id[level_id]
            processed_level_ids.add(level_id)

            # Update level name if it changed
            if level.name != level_name:
                level.name = level_name
                level.save()
        else:
            # This is a new level
            level = Level.objects.create(season=season, name=level_name)
            processed_level_ids.add(level.id)

        # Process teams for this level
        existing_teams_by_id = {
            team.id: team for team in Team.objects.filter(level=level)
        }
        processed_team_ids = set()

        for team_info in team_infos:
            team_id = team_info.get("id")
            team_name = team_info.get("name", "").strip()

            if not team_name:
                continue

            # Check if this is a rename or update of existing team
            if team_id and team_id in existing_teams_by_id:
                team = existing_teams_by_id[team_id]
                processed_team_ids.add(team_id)

                # Update team name if it changed
                if team.name != team_name:
                    team.name = team_name
                    team.save()
            else:
                # This is a new team
                team = Team.objects.create(level=level, name=team_name)
                processed_team_ids.add(team.id)

        # Remove teams that are no longer present
        handle_team_deletions(existing_teams_by_id, processed_team_ids)

    return processed_level_ids


def process_level_updates_old_format(teams_data, existing_levels_by_name, season):
    """Process level updates using old format (name-based)."""
    processed_level_ids = set()

    for level_name, team_names in teams_data.items():
        level_name = level_name.strip()
        if not level_name:
            continue

        # Get or create the level
        if level_name in existing_levels_by_name:
            level = existing_levels_by_name[level_name]
            processed_level_ids.add(level.id)
        else:
            level = Level.objects.create(season=season, name=level_name)
            processed_level_ids.add(level.id)

        # Process teams for this level (old format)
        existing_teams = {
            team.name: team for team in Team.objects.filter(level=level)
        }
        updated_teams = set()

        for team_name in team_names:
            if team_name.strip():
                team_name = team_name.strip()
                updated_teams.add(team_name)

                if team_name not in existing_teams:
                    Team.objects.create(level=level, name=team_name)

        # Remove teams that are no longer present
        handle_team_deletions_old_format(existing_teams, updated_teams)

    return processed_level_ids


def handle_level_deletions(existing_levels_by_id, processed_level_ids):
    """Safely delete levels that are no longer present."""
    levels_to_remove = set(existing_levels_by_id.keys()) - processed_level_ids
    for level_id in levels_to_remove:
        level = existing_levels_by_id[level_id]
        # Check if level has any teams with games
        teams_with_games = (
            Team.objects.filter(level=level)
            .filter(
                Q(games_as_team1__isnull=False)
                | Q(games_as_team2__isnull=False)
                | Q(games_as_referee__isnull=False)
            )
            .exists()
        )

        if not teams_with_games:
            # Safe to delete the level and its teams
            level.delete()  # This will cascade delete teams
        # If teams have games, we keep the level


def update_teams_and_levels(season_id, data):
    """Update teams and levels for a season."""
    season = get_object_or_404(Season, pk=season_id)

    levels_data = data.get("levels", [])
    teams_data = data.get("teams", {})  # Fallback to old format

    # Start transaction to ensure data consistency
    with transaction.atomic():
        # Get existing levels for this season
        existing_levels_by_id = {
            level.id: level for level in Level.objects.filter(season=season)
        }
        existing_levels_by_name = {
            level.name: level for level in Level.objects.filter(season=season)
        }

        # Use new format if available, otherwise fall back to old format
        if levels_data:
            # New format with IDs - can handle renames properly
            processed_level_ids = process_level_updates(
                levels_data, existing_levels_by_id, existing_levels_by_name, season
            )
        else:
            # Old format fallback - only names provided
            processed_level_ids = process_level_updates_old_format(
                teams_data, existing_levels_by_name, season
            )

        # Remove levels that are no longer present
        handle_level_deletions(existing_levels_by_id, processed_level_ids)

    return {"status": "success", "message": "Teams and levels updated successfully"}