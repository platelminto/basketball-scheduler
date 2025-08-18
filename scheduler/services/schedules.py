"""
Schedule CRUD service functions.

This module contains business logic for creating, updating, and managing
schedules including game creation and validation.
"""

from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
from scheduler.models import OffWeek, Season, Level, SeasonTeam, TeamOrganization, Game, Week
from scheduler.services.game_operations import (
    normalize_game_data,
    resolve_game_objects,
    parse_game_fields,
)


def normalize_time_field(time_value):
    """Convert empty string to None for TimeField compatibility"""
    if time_value == "" or time_value is None:
        return None
    return time_value


def create_season_and_structure(season_name, setup_data, week_dates_data):
    """Create a new season with its levels, teams, and weeks."""
    teams_by_level_name = setup_data.get("teams")
    if not teams_by_level_name:
        raise ValueError("Missing 'teams' data in setupData")

    # Get slot duration from setup data, default to 70 minutes
    slot_duration = setup_data.get("slot_duration_minutes", 70)

    season, created = Season.objects.get_or_create(
        name=season_name, defaults={"slot_duration_minutes": slot_duration}
    )
    if not created:
        raise ValueError(
            f"A season with the name '{season_name}' already exists. Please choose a different name."
        )

    # Create levels and teams
    level_instances = {}
    team_instances = {}
    for level_name, team_names in teams_by_level_name.items():
        level_obj = Level.objects.create(season=season, name=level_name)
        level_instances[level_name] = level_obj
        team_instances[level_name] = {}
        for team_name in team_names:
            # Get or create TeamOrganization
            team_org, created = TeamOrganization.objects.get_or_create(name=team_name)
            # Create SeasonTeam assignment
            season_team = SeasonTeam.objects.create(season=season, team=team_org, level=level_obj)
            team_instances[level_name][team_name] = season_team

    # Create weeks from week_dates_data
    for week_info in week_dates_data:
        week_number = week_info.get("week_number")
        monday_date = week_info.get("monday_date")
        is_off_week = week_info.get("is_off_week", False)

        if is_off_week:
            # Extract new off week fields with defaults
            title = week_info.get("title", "Off Week")
            description = week_info.get("description", "No games scheduled")
            has_basketball = week_info.get("has_basketball", False)
            
            OffWeek.objects.create(
                season=season, 
                monday_date=monday_date,
                title=title,
                description=description,
                has_basketball=has_basketball,
                start_time=normalize_time_field(week_info.get("start_time")),
                end_time=normalize_time_field(week_info.get("end_time"))
            )
        else:
            Week.objects.create(
                season=season, week_number=week_number, monday_date=monday_date
            )

    return season, level_instances, team_instances


def update_season_weeks(season, week_dates_data):
    """Update weeks for an existing season."""
    if not week_dates_data:
        return

    # Clear all existing off-weeks for this season first to avoid UNIQUE constraint issues
    OffWeek.objects.filter(season=season).delete()

    # Clear all existing regular weeks (games already deleted above)
    Week.objects.filter(season=season).delete()

    # Recreate all weeks from frontend data
    for week_date in week_dates_data:
        week_id = week_date.get("id")
        new_date = week_date.get("date")
        is_off_week = week_date.get("isOffWeek", False)

        if week_id and new_date:
            try:
                parsed_date = datetime.strptime(new_date, "%Y-%m-%d").date()

                if is_off_week:
                    # Create new off week
                    title = week_date.get("title", "Off Week")
                    description = week_date.get("description", "No games scheduled")
                    has_basketball = week_date.get("has_basketball", False)
                    
                    OffWeek.objects.create(
                        season=season, 
                        monday_date=parsed_date,
                        title=title,
                        description=description,
                        has_basketball=has_basketball,
                        start_time=normalize_time_field(week_date.get("start_time")),
                        end_time=normalize_time_field(week_date.get("end_time"))
                    )
                else:
                    # Create new regular week
                    Week.objects.create(
                        season=season,
                        week_number=int(week_id),
                        monday_date=parsed_date,
                    )

            except Exception as e:
                raise ValueError(f"Error processing week {week_id}: {str(e)}")


def build_update_lookups(season):
    """Build lookup dictionaries for updating an existing season."""
    valid_levels = {
        str(level.id): level for level in Level.objects.filter(season=season)
    }
    valid_teams = {
        str(season_team.id): season_team for season_team in SeasonTeam.objects.filter(season=season)
    }
    valid_weeks = {
        str(week.week_number): week
        for week in Week.objects.filter(season=season)
    }
    return valid_levels, valid_teams, valid_weeks


def process_game_assignments(game_assignments, is_create, lookups):
    """Process and create games from assignments."""
    created_games_count = 0
    creation_errors = []

    for idx, assignment in enumerate(game_assignments):
        try:
            # Normalize and resolve objects
            game_data = normalize_game_data(assignment, is_create, lookups)
            (
                level_obj,
                team1_obj,
                team2_obj,
                referee_obj,
                referee_name,
                week_obj,
                resolve_errors,
            ) = resolve_game_objects(game_data, is_create, lookups)

            if resolve_errors:
                creation_errors.extend(
                    [f"Game #{idx+1}: {err}" for err in resolve_errors]
                )
                continue

            # Parse fields
            game_time, day_of_week, team1_score, team2_score, parse_errors = (
                parse_game_fields(game_data, is_create)
            )
            if parse_errors:
                creation_errors.extend(
                    [f"Game #{idx+1}: {err}" for err in parse_errors]
                )
                continue

            # Create game (validation already passed)
            Game.objects.create(
                level=level_obj,
                week=week_obj,
                season_team1=team1_obj,
                season_team2=team2_obj,
                referee_season_team=referee_obj,
                referee_name=referee_name,
                day_of_week=day_of_week,
                time=game_time,
                court=game_data["court"],
                team1_score=team1_score,
                team2_score=team2_score,
            )
            created_games_count += 1

        except Exception as e:
            creation_errors.append(
                f"Game #{idx+1}: Unexpected error during creation - {str(e)}"
            )

    return created_games_count, creation_errors


@transaction.atomic
def create_schedule(season_name, setup_data, game_assignments, week_dates_data):
    """Create a new schedule with season, levels, teams, and games safely using database transaction."""
    season, level_instances, team_instances = create_season_and_structure(
        season_name, setup_data, week_dates_data
    )
    
    lookups = (level_instances, team_instances, season)
    created_games_count, creation_errors = process_game_assignments(
        game_assignments, is_create=True, lookups=lookups
    )

    if creation_errors:
        error_details = ". ".join(creation_errors)
        # The @transaction.atomic decorator will automatically rollback all changes
        # if an exception is raised, so the season/levels/teams will be cleaned up
        raise ValueError(f"Schedule passed validation but had creation errors: {error_details}")

    return season, created_games_count


@transaction.atomic
def update_schedule(season_id, game_assignments, week_dates_data):
    """Update an existing schedule safely using database transaction."""
    season = get_object_or_404(Season, pk=season_id)

    # Create savepoint to rollback to if game creation fails
    savepoint = transaction.savepoint()
    
    try:
        # Delete existing games first (before weeks, since week FK is now PROTECT)
        deleted_count, _ = Game.objects.filter(level__season=season).delete()

        # Handle week date updates, deletions, and off-week insertions
        update_season_weeks(season, week_dates_data)

        # Build lookups for new game creation (games already deleted above)
        lookups = build_update_lookups(season)

        created_games_count, creation_errors = process_game_assignments(
            game_assignments, is_create=False, lookups=lookups
        )

        if creation_errors:
            error_details = ". ".join(creation_errors)
            # Rollback to savepoint to restore deleted games
            transaction.savepoint_rollback(savepoint)
            raise ValueError(f"Schedule passed validation but had creation errors: {error_details}")

        # Commit the savepoint - everything succeeded
        transaction.savepoint_commit(savepoint)
        return season, created_games_count, deleted_count
        
    except Exception as e:
        # Rollback to savepoint to restore deleted games
        transaction.savepoint_rollback(savepoint)
        raise


def build_schedule_response_data(is_create, season, created_games_count, deleted_count=None):
    """Build response data for schedule operations."""
    response_data = {
        "status": "success",
        "games_created": created_games_count,
    }

    if is_create:
        response_data.update(
            {
                "message": f"Schedule saved successfully for season '{season.name}'.",
                "season_id": season.id,
            }
        )
    else:
        response_data.update(
            {
                "deleted_count": deleted_count,
                "message": f"Successfully updated schedule ({created_games_count} games).",
            }
        )

    return response_data