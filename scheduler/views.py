import traceback
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest
import json
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction, IntegrityError
from datetime import datetime
from scheduler.models import OffWeek, Season, Level, Team, Game, Week
from collections import defaultdict
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, get_current_timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from tests import (
    pairing_tests,
    cycle_pairing_test,
    referee_player_test,
    adjacent_slot_test,
)
from utils import get_config_from_schedule_creator


def season_list(request):
    """View to list all available Seasons with their levels and teams for inline expansion."""
    seasons = (
        Season.objects.all()
        .prefetch_related("levels__teams")  # Prefetch levels and their teams
        .order_by("-is_active", "-created_at")
    )
    context = {"seasons": seasons}
    return render(request, "scheduler/season_list.html", context)


def create_season(request):
    """View to start creating a new season"""
    return render(request, "scheduler/create_season.html")


def team_setup(request):
    """View for setting up teams and courts"""
    return render(request, "scheduler/team_setup.html")


def game_assignment(request):
    """View for assigning teams to games"""
    return render(request, "scheduler/game_assignment.html")


def schedule_app(request, path=None):
    """View for the unified React SPA

    The path parameter is used for the catch-all route and is ignored since
    all routes are handled by React Router on the client side.
    """
    return render(request, "scheduler/schedule_app_standalone.html")


def seasons_api(request):
    """API endpoint to get all seasons with their levels and teams."""
    seasons = (
        Season.objects.all()
        .prefetch_related("levels__teams")
        .order_by("-is_active", "-created_at")
    )

    seasons_data = []
    for season in seasons:
        levels_data = []
        for level in season.levels.all():
            teams_data = [
                {"id": team.id, "name": team.name} for team in level.teams.all()
            ]
            levels_data.append(
                {"id": level.id, "name": level.name, "teams": teams_data}
            )

        seasons_data.append(
            {
                "id": season.id,
                "name": season.name,
                "is_active": season.is_active,
                "created_at": season.created_at.isoformat(),
                "levels": levels_data,
            }
        )

    return JsonResponse(seasons_data, safe=False)


def activate_season_api(request, season_id):
    """API endpoint to activate a season."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    season_to_activate = get_object_or_404(Season, pk=season_id)

    try:
        # Deactivate all other seasons first
        Season.objects.filter(is_active=True).update(is_active=False)

        # Activate the selected season
        season_to_activate.is_active = True
        season_to_activate.save()

        return JsonResponse(
            {
                "success": True,
                "season": {
                    "id": season_to_activate.id,
                    "name": season_to_activate.name,
                    "is_active": True,
                },
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@ensure_csrf_cookie
def validate_schedule(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            schedule_data = data["schedule"]
            config_data = data["config"]

            # Extract levels and teams_per_level from the provided config
            levels = config_data["levels"]
            teams_per_level = config_data["teams_per_level"]

            validation_results = {}

            # Run Pairing Test
            pt_passed, pt_errors = pairing_tests(schedule_data, levels, teams_per_level)
            validation_results["Pairings"] = {
                "passed": pt_passed,
                "message": "Teams play the correct number of times based on their level size.",
                "errors": pt_errors,
            }

            # Run Cycle Pairing Test
            cpt_passed, cpt_errors = cycle_pairing_test(
                schedule_data, levels, teams_per_level
            )
            validation_results["Cycle Pairings"] = {
                "passed": cpt_passed,
                "message": "Matchups repeat in proper round-robin cycles for each level.",
                "errors": cpt_errors,
            }

            # Run Referee-Player Test
            rpt_passed, rpt_errors = referee_player_test(schedule_data)
            validation_results["Referee-Player"] = {
                "passed": rpt_passed,
                "message": "No team referees a game in which they are playing.",
                "errors": rpt_errors,
            }

            # Run Adjacent Slots Test
            ast_passed, ast_errors = adjacent_slot_test(schedule_data)
            validation_results["Adjacent Slots"] = {
                "passed": ast_passed,
                "message": "Teams only referee in slots directly adjacent to when they play.",
                "errors": ast_errors,
            }

            return JsonResponse(validation_results)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error during validation: {e}")  # Consider using proper logging
            import traceback

            traceback.print_exc()
            return JsonResponse(
                {"error": f"An internal error occurred during validation: {e}"},
                status=500,
            )  # Return 500 for server errors

    return JsonResponse({"error": "Invalid request method"}, status=405)


@ensure_csrf_cookie
def auto_generate_schedule(request):
    """
    View to get configuration from the schedule creator and generate a schedule
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            setup_data = data.get("setupData", "")
            week_data = data.get("weekData", "")

            # Get configuration from the setup data
            config = get_config_from_schedule_creator(setup_data, week_data)

            from schedule import Scheduler

            # Create a scheduler with our config
            scheduler = Scheduler(config)

            # Generate the schedule
            schedule, _ = scheduler.find_schedule(
                num_cores=1, use_saved_schedule=False, max_attempts=30000
            )

            if not schedule:
                return JsonResponse({"error": "No schedule found"}, status=400)

            scheduled_week_data = []

            seen_off_weeks = 0
            for data_week in week_data.values():
                if data_week.get("isOffWeek", False):
                    seen_off_weeks += 1
                    continue

                schedule_week = schedule[data_week["week_number"] - 1 - seen_off_weeks]
                schedule_games = [game for slot in schedule_week["slots"].values() for game in slot]
                week = []
                
                for i, data_game in enumerate(data_week["games"]):
                    schedule_game = schedule_games[i]
                    data_game["level_name"] = schedule_game["level"]
                    data_game["team1_name"] = schedule_game["teams"][0]
                    data_game["team2_name"] = schedule_game["teams"][1]
                    data_game["referee_name"] = schedule_game["ref"]
                    
                    week.append(data_game)
                
                scheduled_week_data.append(week)

            return JsonResponse({"config": scheduler.config, "schedule": scheduled_week_data})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            print(f"Error during auto-generation: {e}")
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def _normalize_game_data(assignment, is_create, lookups=None):
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


def _resolve_game_objects(game_data, is_create, lookups):
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
            if game_data["referee_value"].startswith("name:"):
                referee_name = game_data["referee_value"][5:]
            else:
                referee_obj = valid_teams.get(str(game_data["referee_value"]))
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


def _convert_to_validation_format(game_assignments, is_create, lookups):
    """
    Convert game assignments to the format expected by validation functions.
    Returns (schedule_data, config_data, errors)
    """
    from collections import defaultdict

    week_groups = {}
    levels = set()
    teams_per_level = defaultdict(set)
    errors = []

    for idx, assignment in enumerate(game_assignments):
        try:
            # Get normalized data
            game_data = _normalize_game_data(assignment, is_create, lookups)

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
                    if game_data["referee_value"].startswith("name:"):
                        ref_name = game_data["referee_value"][5:]
                    else:
                        ref_obj = valid_teams.get(str(game_data["referee_value"]))
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


def _run_validation_tests(schedule_data, config_data):
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


def _parse_game_fields(game_data, is_create):
    """Parse time, day_of_week, and scores from game data."""
    errors = []

    # Parse time
    game_time = None
    if game_data["time_str"]:
        try:
            from datetime import datetime

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
        team1_score = (
            int(score1_str)
            if isinstance(score1_str, str) and score1_str.isdigit()
            else None
        )
        team2_score = (
            int(score2_str)
            if isinstance(score2_str, str) and score2_str.isdigit()
            else None
        )

    return game_time, day_of_week, team1_score, team2_score, errors


@require_POST
@transaction.atomic
def save_or_update_schedule(
    request: HttpRequest, season_id=None, skip_validation=False
):
    """
    Unified endpoint to create or update a schedule.
    - For create: requires season_name and setupData
    - For update: uses existing season_id
    - Always recreates all games for the season
    - skip_validation: Optional flag to skip comprehensive validation
    """
    try:
        data = json.loads(request.body)
        season_name = data.get("season_name")
        setup_data = data.get("setupData")
        game_assignments = data.get("game_assignments") or data.get("games", [])
        week_dates_data = data.get("week_dates", [])

        is_create = season_id is None

        # Validate required data
        if is_create:
            if not season_name or not setup_data or game_assignments is None:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Missing required data: season_name, setupData, or game_assignments",
                    },
                    status=400,
                )
        else:
            if not game_assignments:
                return JsonResponse(
                    {"status": "error", "message": "Missing required data: games"},
                    status=400,
                )

        # Handle season creation/retrieval
        if is_create:
            teams_by_level_name = setup_data.get("teams")
            if not teams_by_level_name:
                return JsonResponse(
                    {"status": "error", "message": "Missing 'teams' data in setupData"},
                    status=400,
                )

            season, created = Season.objects.get_or_create(name=season_name)
            if not created:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"A season with the name '{season_name}' already exists. Please choose a different name.",
                    },
                    status=409,
                )

            # Create levels and teams
            level_instances = {}
            team_instances = {}
            for level_name, team_names in teams_by_level_name.items():
                level_obj = Level.objects.create(season=season, name=level_name)
                level_instances[level_name] = level_obj
                team_instances[level_name] = {}
                for team_name in team_names:
                    team_obj = Team.objects.create(level=level_obj, name=team_name)
                    team_instances[level_name][team_name] = team_obj

            # Create weeks from week_dates_data
            for week_info in week_dates_data:
                week_number = week_info.get("week_number")
                monday_date = week_info.get("monday_date")
                is_off_week = week_info.get("is_off_week", False)

                if is_off_week:
                    OffWeek.objects.create(season=season, monday_date=monday_date)
                else:
                    Week.objects.create(
                        season=season, week_number=week_number, monday_date=monday_date
                    )

            lookups = (level_instances, team_instances, season)
            deleted_count = 0
        else:
            season = get_object_or_404(Season, pk=season_id)

            # Handle week date updates
            if week_dates_data:
                week_numbers = {
                    str(week.week_number): week
                    for week in Week.objects.filter(season=season)
                }
                for week_date in week_dates_data:
                    week_id = week_date.get("id")
                    new_date = week_date.get("date")
                    if week_id and new_date:
                        try:
                            week = week_numbers.get(str(week_id))
                            if not week:
                                raise ValueError(f"Invalid week number: {week_id}")
                            from datetime import datetime

                            parsed_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                            week.monday_date = parsed_date
                            week.save()
                        except Exception as e:
                            return JsonResponse(
                                {
                                    "status": "error",
                                    "error": f"Error updating week {week_id}: {str(e)}",
                                },
                                status=400,
                            )

            # Delete existing games and build lookups
            deleted_count, _ = Game.objects.filter(level__season=season).delete()
            valid_levels = {
                str(level.id): level for level in Level.objects.filter(season=season)
            }
            valid_teams = {
                str(team.id): team for team in Team.objects.filter(level__season=season)
            }
            valid_weeks = {
                str(week.week_number): week
                for week in Week.objects.filter(season=season)
            }
            lookups = (valid_levels, valid_teams, valid_weeks)

        # Run validation using existing functions (unless skipped for testing)
        if not skip_validation:
            schedule_data, config_data, conversion_errors = (
                _convert_to_validation_format(game_assignments, is_create, lookups)
            )

            if conversion_errors:
                transaction.set_rollback(True)
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Schedule had conversion errors and was not saved.",
                        "errors": conversion_errors,
                    },
                    status=400,
                )

            # Run comprehensive validation
            validation_errors = _run_validation_tests(schedule_data, config_data)
            if validation_errors:
                transaction.set_rollback(True)
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Schedule failed validation tests. Please fix all errors and try again.",
                        "errors": validation_errors,
                    },
                    status=400,
                )

        # Process games - validation passed, now create them
        created_games_count = 0
        creation_errors = []

        for idx, assignment in enumerate(game_assignments):
            try:
                # Normalize and resolve objects
                game_data = _normalize_game_data(assignment, is_create, lookups)
                (
                    level_obj,
                    team1_obj,
                    team2_obj,
                    referee_obj,
                    referee_name,
                    week_obj,
                    resolve_errors,
                ) = _resolve_game_objects(game_data, is_create, lookups)

                if resolve_errors:
                    creation_errors.extend(
                        [f"Game #{idx+1}: {err}" for err in resolve_errors]
                    )
                    continue

                # Parse fields
                game_time, day_of_week, team1_score, team2_score, parse_errors = (
                    _parse_game_fields(game_data, is_create)
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
                    team1=team1_obj,
                    team2=team2_obj,
                    referee_team=referee_obj,
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

        # Handle creation errors (shouldn't happen if validation passed)
        if creation_errors:
            transaction.set_rollback(True)
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Schedule passed validation but had creation errors.",
                    "errors": creation_errors,
                },
                status=400,
            )

        # Return success response
        response_data = {
            "status": "success",
            "games_created": created_games_count,
        }

        if is_create:
            response_data.update(
                {
                    "message": f"Schedule saved successfully for season '{season_name}'.",
                    "season_id": season.id,
                }
            )
        else:
            response_data.update(
                {
                    "deleted_count": deleted_count,
                    "message": f"Successfully updated schedule with {created_games_count} games.",
                }
            )

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON data"}, status=400
        )
    except IntegrityError as e:
        return JsonResponse(
            {"status": "error", "message": f"Database integrity error: {e}"}, status=400
        )
    except ValueError as e:
        return JsonResponse(
            {"status": "error", "message": f"Validation error: {e}"}, status=400
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(traceback.format_exc())
        return JsonResponse(
            {"status": "error", "message": f"An unexpected error occurred: {e}"},
            status=500,
        )


def schedule_edit(request, season_id):
    """View for displaying the schedule edit form."""
    season = get_object_or_404(Season, pk=season_id)

    # Fetch all games for this season, related data upfront for efficiency
    games = (
        Game.objects.filter(level__season=season)
        .select_related("level", "team1", "team2", "referee_team", "week")
        .order_by("week__week_number", "day_of_week", "time", "level__name")
    )

    # Fetch all levels and teams for this season
    levels = (
        Level.objects.filter(season=season).prefetch_related("teams").order_by("name")
    )

    # Create the original dict with model instances (useful for template loops)
    teams_by_level_objects = {
        level.id: list(level.teams.all().order_by("name")) for level in levels
    }

    # --- Create a JSON-serializable version for json_script ---
    teams_by_level_serializable = {
        str(level_id): [{"id": team.id, "name": team.name} for team in team_list]
        for level_id, team_list in teams_by_level_objects.items()
    }
    # ----------------------------------------------------------

    # --- Create serializable levels data for JS name lookup ---
    levels_data_for_js = [{"id": level.id, "name": level.name} for level in levels]
    # -------------------------------------------------------

    # Get distinct court names used in this season's games
    courts = list(games.values_list("court", flat=True).distinct().order_by("court"))
    courts = [court for court in courts if court]

    # Group games by week
    games_by_week = {}
    for game in games:
        if game.week not in games_by_week:
            games_by_week[game.week] = []
        games_by_week[game.week].append(game)

    context = {
        "season": season,
        "games_by_week": games_by_week,
        "levels": levels,  # Pass Level objects for level dropdown
        # Pass the dictionary with Team objects for initial dropdown population
        "teams_by_level_objects": teams_by_level_objects,
        # Pass the serializable dict specifically for json_script
        "teams_data_for_js": teams_by_level_serializable,
        "levels_data_for_js": levels_data_for_js,  # Add levels data
        "courts": courts,
    }

    return render(request, "scheduler/schedule_edit.html", context)


@require_GET
def get_season_schedule_data(request: HttpRequest, season_id: int):
    """API endpoint to fetch current data for all games in a season."""
    # Basic permission check (optional, enhance as needed)
    # if not request.user.is_staff:
    #     return JsonResponse({"error": "Permission denied"}, status=403)

    season = get_object_or_404(Season, pk=season_id)
    games = Game.objects.filter(level__season=season).select_related(
        "level", "team1", "team2", "referee_team", "week"
    )

    game_data = []
    for game in games:
        # Handle referee (team or string name)
        referee_value = ""
        if game.referee_team:
            referee_value = str(game.referee_team.id)
        elif game.referee_name:
            # Add a prefix to indicate this is a string name, not an ID
            referee_value = "name:" + game.referee_name

        game_data.append(
            {
                "id": str(game.id),  # Use string IDs for consistency with JS
                "week": str(game.week.week_number),
                "day": str(game.day_of_week) if game.day_of_week is not None else "",
                "time": game.time.strftime("%H:%M") if game.time else "",
                "court": game.court or "",  # Ensure consistent type (string)
                "level": str(game.level.id),
                "team1": str(game.team1.id),
                "team2": str(game.team2.id),
                "referee": referee_value,
                "score1": str(game.team1_score) if game.team1_score is not None else "",
                "score2": str(game.team2_score) if game.team2_score is not None else "",
            }
        )

    return JsonResponse({"games": game_data})


@require_POST
def activate_season(request, season_id):
    """Sets the specified season as active."""
    season_to_activate = get_object_or_404(Season, pk=season_id)
    if not season_to_activate.is_active:
        season_to_activate.is_active = True
        try:
            season_to_activate.save()
            messages.success(
                request, f"Season '{season_to_activate.name}' is now active."
            )
        except Exception as e:
            messages.error(request, f"Could not activate season: {e}")

    return redirect("scheduler:season_list")


# Placeholder for the new view to edit season structure (Levels/Teams)
def edit_season_structure(request, season_id):
    # TODO: Implement view to edit levels and teams for an existing season
    season = get_object_or_404(Season, pk=season_id)
    # For now, just redirect back to the detail page or render a simple placeholder
    # Example: Render a placeholder template
    return render(
        request,
        "scheduler/edit_season_structure_placeholder.html",
        {"season": season},
    )
    # Or redirect:
    # from django.shortcuts import redirect
    # return redirect('scheduler:season_detail', season_id=season_id)


def schedule_edit_react(request, season_id):
    """Schedule edit view that redirects to the unified React SPA"""
    from django.shortcuts import redirect

    # Redirect to the SPA with the correct route
    return redirect(f"/scheduler/app/schedule/{season_id}/edit")


@ensure_csrf_cookie
def schedule_data(request, season_id):
    """API endpoint for schedule data used by React"""
    season = get_object_or_404(Season, pk=season_id)

    # Get all weeks in this season
    weeks = Week.objects.filter(season=season).order_by("week_number")

    # Get all games grouped by week
    games_by_week = {}
    for week in weeks:
        games = (
            Game.objects.filter(week=week)
            .select_related("level", "team1", "team2", "referee_team")
            .order_by("day_of_week", "time")
        )

        games_list = []
        for game in games:
            games_list.append(
                {
                    "id": game.id,
                    "day_of_week": game.day_of_week,
                    "time": game.time.strftime("%H:%M") if game.time else "",
                    "court": game.court,
                    "level_id": game.level.id if game.level else None,
                    "level_name": game.level.name if game.level else "",
                    "team1_id": game.team1.id if game.team1 else None,
                    "team1_name": game.team1.name if game.team1 else "",
                    "team2_id": game.team2.id if game.team2 else None,
                    "team2_name": game.team2.name if game.team2 else "",
                    "team1_score": game.team1_score,
                    "team2_score": game.team2_score,
                    "referee_team_id": (
                        game.referee_team.id if game.referee_team else None
                    ),
                    "referee_name": game.referee_name,
                }
            )

        games_by_week[week.week_number] = {
            "id": week.id,
            "week_number": week.week_number,
            "monday_date": week.monday_date.strftime("%Y-%m-%d"),
            "games": games_list,
        }

    # Get all levels
    levels = Level.objects.filter(season=season).order_by("name")
    levels_data = [{"id": level.id, "name": level.name} for level in levels]

    # Get all teams by level
    teams_by_level = {}
    for level in levels:
        teams = Team.objects.filter(level=level).order_by("name")
        teams_by_level[level.id] = [
            {"id": team.id, "name": team.name} for team in teams
        ]

    # Get all courts
    courts = list(
        Game.objects.filter(level__season=season)
        .values_list("court", flat=True)
        .distinct()
        .order_by("court")
    )
    courts = [court for court in courts if court]

    return JsonResponse(
        {
            "season": {
                "id": season.id,
                "name": season.name,
            },
            "weeks": games_by_week,
            "levels": levels_data,
            "teams_by_level": teams_by_level,
            "courts": courts,
        }
    )
