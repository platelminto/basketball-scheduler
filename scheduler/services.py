"""
Service functions for schedule management business logic.

This module contains the complex business logic that was previously in views.py,
following Django best practices of separating business logic from HTTP handling.
"""

from datetime import datetime
from collections import defaultdict
from scheduler.models import Week
from tests import (
    pairing_tests,
    cycle_pairing_test,
    referee_player_test,
    adjacent_slot_test,
)


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

        if not team1_obj or team1_obj.level_id != level_obj.id:
            errors.append(
                f"Invalid Team 1 ID: {game_data['team1_id']} for Level {level_obj.name}"
            )
        if not team2_obj or team2_obj.level_id != level_obj.id:
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
                    and referee_obj.level_id != level_obj.id
                ):
                    errors.append(
                        f"Invalid Referee ID: {game_data['referee_value']} for Level {level_obj.name}"
                    )

        # Resolve week
        week_obj = valid_weeks.get(str(game_data["week_number"]))
        if not week_obj:
            errors.append(f"Invalid week number: {game_data['week_number']}")

    return level_obj, team1_obj, team2_obj, referee_obj, referee_name, week_obj, errors


def convert_to_validation_format(game_assignments, is_create, lookups):
    """
    Convert game assignments to the format expected by validation functions.
    Returns (schedule_data, config_data, errors)
    """
    week_groups = {}
    levels = set()
    teams_per_level = defaultdict(set)
    errors = []

    for idx, assignment in enumerate(game_assignments):
        try:
            # Get normalized data
            game_data = normalize_game_data(assignment, is_create, lookups)

            # Extract team/level names based on mode
            if is_create:
                level_instances, team_instances, season = lookups
                level_name = game_data["level_name"]
                team1_name = game_data["team1_name"]
                team2_name = game_data["team2_name"]
                ref_name = game_data["referee_name"] or "External Ref"

                # Basic validation for create mode
                if not all([level_name, team1_name, team2_name]):
                    errors.append(f"Game #{idx+1}: Missing required fields")
                    continue

            else:
                valid_levels, valid_teams, valid_weeks = lookups
                level_obj = valid_levels.get(str(game_data["level_id"]))
                team1_obj = valid_teams.get(str(game_data["team1_id"]))
                team2_obj = valid_teams.get(str(game_data["team2_id"]))

                if not all([level_obj, team1_obj, team2_obj]):
                    errors.append(f"Game #{idx+1}: Invalid level or team IDs")
                    continue

                level_name = level_obj.name
                team1_name = team1_obj.name
                team2_name = team2_obj.name

                # Handle referee
                ref_name = "External Ref"
                if game_data["referee_value"]:
                    # Convert referee_value to string to handle both string and integer IDs
                    referee_str = str(game_data["referee_value"])
                    if referee_str.startswith("name:"):
                        ref_name = referee_str[5:]
                    else:
                        ref_obj = valid_teams.get(referee_str)
                        ref_name = ref_obj.name if ref_obj else "External Ref"

            week_key = game_data["week_number"]

            # Initialize week group
            if week_key not in week_groups:
                week_groups[week_key] = {"week": week_key, "slots": {}}

            # Create slot (use day_of_week or default to 1)
            slot_num = str(game_data.get("day_of_week", "1"))
            if slot_num not in week_groups[week_key]["slots"]:
                week_groups[week_key]["slots"][slot_num] = []

            # Add game to slot
            week_groups[week_key]["slots"][slot_num].append(
                {
                    "level": level_name,
                    "teams": [team1_name, team2_name],
                    "ref": ref_name,
                }
            )

            # Track levels and teams for config
            levels.add(level_name)
            teams_per_level[level_name].add(team1_name)
            teams_per_level[level_name].add(team2_name)

        except Exception as e:
            errors.append(f"Game #{idx+1}: Error processing - {str(e)}")

    # Convert to list format
    schedule_data = list(week_groups.values())

    # Create config
    config_data = {
        "levels": list(levels),
        "teams_per_level": {
            level: len(teams) for level, teams in teams_per_level.items()
        },
    }

    return schedule_data, config_data, errors


def run_validation_tests(schedule_data, config_data):
    """Run the existing validation functions and collect all errors."""
    all_errors = []

    try:
        levels = config_data["levels"]
        teams_per_level = config_data["teams_per_level"]

        # Run all validation tests (same as validate_schedule view)
        pt_passed, pt_errors = pairing_tests(schedule_data, levels, teams_per_level)
        if not pt_passed and pt_errors:
            all_errors.extend([f"Pairing: {err}" for err in pt_errors])

        cpt_passed, cpt_errors = cycle_pairing_test(
            schedule_data, levels, teams_per_level
        )
        if not cpt_passed and cpt_errors:
            all_errors.extend([f"Cycle: {err}" for err in cpt_errors])

        rpt_passed, rpt_errors = referee_player_test(schedule_data)
        if not rpt_passed and rpt_errors:
            all_errors.extend([f"Referee-Player: {err}" for err in rpt_errors])

        ast_passed, ast_errors = adjacent_slot_test(schedule_data)
        if not ast_passed and ast_errors:
            all_errors.extend([f"Adjacent Slots: {err}" for err in ast_errors])

    except Exception as e:
        all_errors.append(f"Validation error: {str(e)}")

    return all_errors


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