"""
Service functions for schedule management business logic.

This module contains the complex business logic that was previously in views.py,
following Django best practices of separating business logic from HTTP handling.
"""

from datetime import datetime
from scheduler.models import Week


def normalize_game_data(assignment, is_create, lookups=None):
    """
    Normalize game assignment data to a common format.
    Returns a dict with normalized fields and model instances.
    """
    if is_create:
        return {
            "level_name": assignment.get("level"),
            "team1_name": assignment.get("team1"),
            "team2_name": assignment.get("team2"),
            "referee_name": assignment.get("referee"),
            "week_number": assignment.get("week"),
            "day_of_week": assignment.get("dayOfWeek"),
            "time_str": assignment.get("time"),
            "court": assignment.get("court"),
            "score1": None,
            "score2": None,
        }
    else:
        return {
            "level_id": assignment.get("level"),
            "team1_id": assignment.get("team1"),
            "team2_id": assignment.get("team2"),
            "referee_value": assignment.get("referee"),
            "week_number": assignment.get("week"),
            "day_of_week": assignment.get("day"),
            "time_str": assignment.get("time"),
            "court": assignment.get("court"),
            "score1": assignment.get("score1"),
            "score2": assignment.get("score2"),
        }


def resolve_game_objects(game_data, is_create, lookups):
    """
    Resolve game data to model instances.
    Returns (level_obj, team1_obj, team2_obj, referee_obj, referee_name, week_obj, errors)
    """
    errors = []

    if is_create:
        level_instances, team_instances, season = lookups

        # Resolve level
        level_obj = level_instances.get(game_data["level_name"])
        if not level_obj:
            errors.append(f"Level '{game_data['level_name']}' not found")
            return None, None, None, None, None, None, errors

        # Resolve teams
        team1_obj = team_instances.get(game_data["level_name"], {}).get(
            game_data["team1_name"]
        )
        team2_obj = team_instances.get(game_data["level_name"], {}).get(
            game_data["team2_name"]
        )

        if not team1_obj:
            errors.append(
                f"Team '{game_data['team1_name']}' not found in level '{game_data['level_name']}'"
            )
        if not team2_obj:
            errors.append(
                f"Team '{game_data['team2_name']}' not found in level '{game_data['level_name']}'"
            )

        # Resolve referee
        referee_obj = None
        referee_name = None
        if game_data["referee_name"]:
            referee_obj = team_instances.get(game_data["level_name"], {}).get(
                game_data["referee_name"]
            )
            if not referee_obj:
                referee_name = game_data["referee_name"]  # External referee

        # Resolve week
        week_obj = Week.objects.get(season=season, week_number=game_data["week_number"])

    else:
        valid_levels, valid_teams, valid_weeks = lookups

        # Resolve level
        level_obj = valid_levels.get(str(game_data["level_id"]))
        if not level_obj:
            errors.append(f"Invalid Level ID: {game_data['level_id']}")
            return None, None, None, None, None, None, errors

        # Resolve teams
        team1_obj = valid_teams.get(str(game_data["team1_id"]))
        team2_obj = valid_teams.get(str(game_data["team2_id"]))

        if not team1_obj or team1_obj.level.id != level_obj.id:
            errors.append(
                f"Invalid Team 1 ID: {game_data['team1_id']} for Level {level_obj.name}"
            )
        if not team2_obj or team2_obj.level.id != level_obj.id:
            errors.append(
                f"Invalid Team 2 ID: {game_data['team2_id']} for Level {level_obj.name}"
            )

        # Resolve referee
        referee_obj = None
        referee_name = None
        if game_data["referee_value"]:
            # Convert referee_value to string to handle both string and integer IDs
            referee_str = str(game_data["referee_value"])
            if referee_str.startswith("name:"):
                referee_name = referee_str[5:]
            else:
                referee_obj = valid_teams.get(referee_str)
                if (
                    game_data["referee_value"]
                    and referee_obj
                    and referee_obj.level.id != level_obj.id
                ):
                    errors.append(
                        f"Invalid Referee ID: {game_data['referee_value']} for Level {level_obj.name}"
                    )

        # Resolve week
        week_obj = valid_weeks.get(str(game_data["week_number"]))
        if not week_obj:
            errors.append(f"Invalid week number: {game_data['week_number']}")

    return level_obj, team1_obj, team2_obj, referee_obj, referee_name, week_obj, errors


def parse_game_fields(game_data, is_create):
    """Parse time, day_of_week, and scores from game data."""
    errors = []

    # Parse time
    game_time = None
    if game_data["time_str"]:
        try:
            game_time = datetime.strptime(game_data["time_str"], "%H:%M").time()
        except (ValueError, TypeError):
            errors.append(f"Invalid time format: {game_data['time_str']}")

    # Parse day of week
    day_of_week = None
    if is_create:
        if game_data["day_of_week"] is not None:
            try:
                day_of_week = int(game_data["day_of_week"])
            except (ValueError, TypeError):
                errors.append(f"Invalid day of week: {game_data['day_of_week']}")
    else:
        day_of_week = game_data["day_of_week"]
        if day_of_week is not None and (day_of_week < 0 or day_of_week > 6):
            errors.append(f"Invalid day of week: {day_of_week}")

    # Parse scores
    team1_score = None
    team2_score = None
    if not is_create:
        score1_str = game_data["score1"]
        score2_str = game_data["score2"]
        
        # Handle scores - convert to string first if needed, then check if numeric
        if score1_str is not None and score1_str != '':
            score1_str = str(score1_str)
            team1_score = int(score1_str) if score1_str.isdigit() else None
        
        if score2_str is not None and score2_str != '':
            score2_str = str(score2_str)
            team2_score = int(score2_str) if score2_str.isdigit() else None

    return game_time, day_of_week, team1_score, team2_score, errors