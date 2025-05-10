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

            if not setup_data:
                return JsonResponse({"error": "No setup data provided"}, status=400)

            # Parse the setup data
            setup_data = json.loads(setup_data)

            # Get configuration from the setup data
            config = get_config_from_schedule_creator(setup_data)

            from schedule import Scheduler

            # Create a scheduler with our config
            scheduler = Scheduler(config)

            # Generate the schedule
            schedule, _ = scheduler.find_schedule(
                num_cores=2, use_saved_schedule=False, max_attempts=30000
            )

            return JsonResponse({"config": scheduler.config, "schedule": schedule})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@require_POST
@transaction.atomic
def save_schedule(request: HttpRequest):
    """
    Receives schedule data via POST, creates/updates Season, Level, Team, Game objects.
    Aborts the entire transaction if any errors are found.
    """
    try:
        data = json.loads(request.body)
        season_name = data.get("season_name")
        setup_data = data.get("setupData")
        game_assignments = data.get("game_assignments")

        if not all([season_name, setup_data, game_assignments]):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Missing required data: season_name, setupData, or game_assignments",
                },
                status=400,
            )

        teams_by_level_name = setup_data.get("teams")
        if not teams_by_level_name:
            return JsonResponse(
                {"status": "error", "message": "Missing 'teams' data in setupData"},
                status=400,
            )

        # --- 1. Handle Season ---
        season, created = Season.objects.get_or_create(name=season_name)
        if not created:
            # If season already existed, return an error instead of overwriting
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"A season with the name '{season_name}' already exists. Please choose a different name.",
                },
                status=409,  # Conflict status code
            )

        # --- 2. Create Levels and Teams ---
        level_instances = {}  # Map level name -> Level object
        team_instances = {}  # Map level name -> { team name -> Team object }

        for level_name, team_names in teams_by_level_name.items():
            level_obj = Level.objects.create(season=season, name=level_name)
            level_instances[level_name] = level_obj
            team_instances[level_name] = {}
            for team_name in team_names:
                team_obj = Team.objects.create(level=level_obj, name=team_name)
                team_instances[level_name][team_name] = team_obj

        # --- 3. Create Weeks ---
        week_count = 0
        for week_info in setup_data["schedule"]["weeks"]:
            if week_info["isOffWeek"]:
                OffWeek.objects.create(
                    season=season, monday_date=week_info["weekStartDate"]
                )
            else:
                week_count += 1
                Week.objects.create(
                    season=season,
                    week_number=week_count,
                    monday_date=week_info["weekStartDate"],
                )

        # --- 4. Create Games ---
        created_games_count = 0
        errors = []
        for assignment in game_assignments:
            level_name = assignment.get("level")
            team1_name = assignment.get("team1")
            team2_name = assignment.get("team2")
            ref_name = assignment.get("referee")
            week_number = assignment.get("week")
            day_of_week_str = assignment.get("dayOfWeek")
            time_str = assignment.get("time")
            court_name = assignment.get("court")  # Assuming court name is passed

            # Validate basic data presence - referee can be null
            missing_fields = []
            if not level_name:
                missing_fields.append("level")
            if not team1_name:
                missing_fields.append("team1")
            if not team2_name:
                missing_fields.append("team2")
            if week_number is None:
                missing_fields.append("week")

            if missing_fields:
                # Create a clear error message listing the missing fields
                game_identifier = f"Week {assignment.get('week', '?')}, day {day_of_week_str or '?'} at {time_str or '?'}"
                error_msg = f"Game in {game_identifier} is missing required fields: {', '.join(missing_fields)}"
                errors.append(error_msg)
                continue

            # Find corresponding model instances
            level_obj = level_instances.get(level_name)
            if not level_obj:
                errors.append(
                    f"Level '{level_name}' not found for game in Week {week_number}, day {day_of_week_str} at {time_str}"
                )
                continue

            team1_obj = team_instances.get(level_name, {}).get(team1_name)
            team2_obj = team_instances.get(level_name, {}).get(team2_name)
            ref_obj = None

            # Handle referee - could be a team object or a string
            if ref_name:
                # First try to get ref as team object
                ref_obj = team_instances.get(level_name, {}).get(ref_name)
                # If not found, it's okay since the referee can be null or a string name

            # Validate teams exist in the level
            validation_errors = []
            if not team1_obj:
                validation_errors.append(
                    f"Team '{team1_name}' not found in level '{level_name}'"
                )
            if not team2_obj:
                validation_errors.append(
                    f"Team '{team2_name}' not found in level '{level_name}'"
                )

            if validation_errors:
                # Create a clear context for the error
                game_identifier = f"Week {week_number}, day {day_of_week_str or '?'} at {time_str or '?'}"
                errors.append(
                    f"Game in {game_identifier}: {'; '.join(validation_errors)}"
                )
                continue

            # Business logic validations
            if team1_name == team2_name:
                errors.append(
                    f"Week {week_number}, day {day_of_week_str} at {time_str}: Team 1 and Team 2 cannot be the same ('{team1_name}')"
                )
                continue

            # Combine date and time
            game_time = None
            if time_str:
                try:
                    # Parse just the time component (HH:MM)
                    from datetime import datetime as dt

                    time_obj = dt.strptime(time_str, "%H:%M").time()
                    game_time = time_obj
                except ValueError:
                    errors.append(
                        f"Week {week_number}: Invalid time format ('{time_str}')"
                    )
                    continue  # Skip if time format is wrong

            try:
                # Determine if we have a team ref or a string ref
                referee_name = None

                # If ref_obj is None but ref_name exists, it's an external ref
                if ref_obj is None and ref_name:
                    referee_name = ref_name

                # Get the week object
                week_obj = Week.objects.get(season=season, week_number=week_number)

                Game.objects.create(
                    level=level_obj,
                    week=week_obj,
                    team1=team1_obj,
                    team2=team2_obj,
                    referee_team=ref_obj,  # Can be None
                    referee_name=referee_name,  # Set the string ref name if applicable
                    time=game_time,
                    day_of_week=int(day_of_week_str),
                    court=court_name,
                )
                created_games_count += 1
            except IntegrityError as e:
                errors.append(
                    f"Week {week_number}, day {day_of_week_str} at {time_str}: Database error creating game - {e}"
                )
            except Exception as e:  # Catch other potential errors during game creation
                errors.append(
                    f"Week {week_number}, day {day_of_week_str} at {time_str}: Unexpected error - {e}"
                )

        # If there are any errors, raise an exception to roll back the transaction
        if errors:
            # Raise a custom exception to trigger rollback, capturing all errors to report
            raise ValueError(f"Schedule has {len(errors)} validation errors")

        return JsonResponse(
            {
                "status": "success",
                "message": f"Schedule saved successfully for season '{season_name}'.",
                "season_id": season.id,
                "games_created": created_games_count,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON data"}, status=400
        )
    except IntegrityError as e:
        # e.g., if Season name constraint fails unexpectedly, though get_or_create handles it.
        return JsonResponse(
            {"status": "error", "message": f"Database integrity error: {e}"}, status=400
        )
    except ValueError as e:
        # Handle the specific case where we raised an exception due to validation errors
        if "validation errors" in str(e):
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Schedule had validation errors and was not saved. Please fix all errors and try again.",
                    "errors": errors,
                },
                status=400,
            )
        # Handle other ValueError cases
        return JsonResponse(
            {"status": "error", "message": f"Validation error: {e}"}, status=400
        )
    except Exception as e:
        # Catch-all for other unexpected errors
        # Log the error in a real application: logger.error(f"Error saving schedule: {e}", exc_info=True)
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
@transaction.atomic
def update_schedule(request: HttpRequest, season_id: int):
    """
    API endpoint to replace all games in a specific season.
    Deletes existing games for the season and creates new ones based on payload.
    Also updates week dates if week_dates is provided in the payload.
    Complete transaction will be rolled back if any game fails.
    """
    # Basic permission check (enhance as needed)
    # if not request.user.is_staff:
    #     return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        data = json.loads(request.body)
        new_games_data = data.get("games", [])
        week_dates_data = data.get("week_dates", [])

        if not isinstance(new_games_data, list):
            raise ValueError("'games' data must be a list.")
        if week_dates_data and not isinstance(week_dates_data, list):
            raise ValueError("'week_dates' data must be a list.")
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"error": f"Invalid JSON or data format: {e}"}, status=400)

    # Create a transaction savepoint that we can roll back to if needed
    try:
        # --- 1. Get Season and related data ---
        season = get_object_or_404(Season, pk=season_id)
        # Fetch valid levels and teams for this season ONCE for efficient lookup
        valid_levels = {
            str(level.id): level for level in Level.objects.filter(season=season)
        }
        valid_teams = {
            str(team.id): team for team in Team.objects.filter(level__season=season)
        }
        # Fetch valid weeks for this season
        weeks = Week.objects.filter(season=season)
        valid_weeks = {str(week.week_number): week for week in weeks}
        week_ids = {str(week.id): week for week in weeks}

        # --- 2. Process week date changes ---
        if week_dates_data:
            for week_date in week_dates_data:
                week_id = week_date.get("id")
                new_date = week_date.get("date")

                if not week_id or not new_date:
                    continue

                try:
                    # Find the week by ID
                    week = week_ids.get(str(week_id))
                    if not week:
                        raise ValueError(f"Invalid week ID: {week_id}")

                    # Parse and update the date
                    from datetime import datetime

                    try:
                        parsed_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                        week.monday_date = parsed_date
                        week.save()
                    except ValueError:
                        raise ValueError(
                            f"Invalid date format for week {week_id}: {new_date}"
                        )
                except Exception as e:
                    # Record the error for this week
                    errors = []
                    error_msg = f"Error updating week {week_id}: {str(e)}"
                    errors.append(error_msg)
                    # Break early to trigger rollback
                    if errors:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"status": "error", "error": "\n".join(errors)}, status=400
                        )

        # --- 3. Delete existing games for this season ---
        # Note: This assumes Levels and Teams are NOT deleted/recreated here, only Games.
        deleted_count, _ = Game.objects.filter(level__season=season).delete()
        # Log deletion if desired: print(f"Deleted {deleted_count} existing games for season {season_id}")

        # --- 4. Create new games from payload ---
        created_count = 0
        errors = []

        for idx, game_data in enumerate(new_games_data):
            try:
                # Extract data (ensure keys exist and handle potential None)
                week_str = game_data.get("week")
                level_id_str = game_data.get("level")
                team1_id_str = game_data.get("team1")
                team2_id_str = game_data.get("team2")
                referee_id_str = game_data.get("referee")  # Can be None or ""
                day_of_week_str = game_data.get("day")  # New: day of week (0-6)
                time_str = game_data.get("time")  # New: time (HH:MM format)
                court = game_data.get("court")  # Can be None or ""
                score1_str = game_data.get("score1")  # Can be None or ""
                score2_str = game_data.get("score2")  # Can be None or ""

                # --- Basic Validation ---
                if not all(
                    [
                        week_str,
                        level_id_str,
                        team1_id_str,
                        team2_id_str,
                        day_of_week_str,
                        time_str,
                    ]
                ):
                    raise ValueError(
                        "Missing required fields (check week, level, team1, team2, day of week, time)"
                    )

                # --- Find Model Instances ---
                level_obj = valid_levels.get(str(level_id_str))
                if not level_obj:
                    raise ValueError(f"Invalid Level ID: {level_id_str}")

                team1_obj = valid_teams.get(str(team1_id_str))
                if not team1_obj or team1_obj.level_id != level_obj.id:
                    raise ValueError(
                        f"Invalid Team 1 ID: {team1_id_str} for Level {level_obj.name}"
                    )

                team2_obj = valid_teams.get(str(team2_id_str))
                if not team2_obj or team2_obj.level_id != level_obj.id:
                    raise ValueError(
                        f"Invalid Team 2 ID: {team2_id_str} for Level {level_obj.name}"
                    )

                # Handle referee - could be a team ID or a string name (prefixed with "name:")
                referee_obj = None
                referee_name = None

                if referee_id_str:  # Only process if provided
                    if referee_id_str.startswith("name:"):
                        # This is a string referee name, not a team ID
                        referee_name = referee_id_str[5:]  # Remove the "name:" prefix
                    else:
                        # This is a team ID
                        referee_obj = valid_teams.get(str(referee_id_str))
                        if (
                            referee_id_str
                            and referee_obj
                            and referee_obj.level_id != level_obj.id
                        ):
                            raise ValueError(
                                f"Invalid Referee ID: {referee_id_str} for Level {level_obj.name}"
                            )

                # --- Business Logic Validation ---
                if team1_obj.id == team2_obj.id:
                    raise ValueError(
                        f"Team 1 and Team 2 cannot be the same (Team ID: {team1_obj.id})"
                    )

                if referee_obj and (
                    referee_obj.id == team1_obj.id or referee_obj.id == team2_obj.id
                ):
                    raise ValueError(
                        f"Team cannot referee its own game (Team ID: {referee_obj.id})"
                    )

                # --- Parse Week ---
                try:
                    week_number = int(week_str)
                    if week_number <= 0:
                        raise ValueError()

                    # Get the Week object
                    week_obj = valid_weeks.get(str(week_number))
                    if not week_obj:
                        raise ValueError(f"Invalid week number: {week_number}")
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid week number: {week_str}")

                # --- Parse Day of Week ---
                day_of_week = None
                if day_of_week_str:
                    try:
                        day_of_week = int(day_of_week_str)
                        if day_of_week < 0 or day_of_week > 6:
                            raise ValueError()
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid day of week: {day_of_week_str}")

                # --- Parse Time ---
                time_obj = None
                if time_str:
                    try:
                        from datetime import datetime

                        time_obj = datetime.strptime(time_str, "%H:%M").time()
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid time format: {time_str}")

                # --- Parse Scores ---
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

                # --- Create Game ---
                Game.objects.create(
                    level=level_obj,
                    week=week_obj,
                    team1=team1_obj,
                    team2=team2_obj,
                    referee_team=referee_obj,  # Can be None
                    referee_name=referee_name,  # String referee (can be None)
                    day_of_week=day_of_week,
                    time=time_obj,
                    court=court,
                    team1_score=team1_score,
                    team2_score=team2_score,
                )
                created_count += 1

            except Exception as e:
                # Record the error for this game
                error_msg = f"Error processing game #{idx+1}: {str(e)}"
                errors.append(error_msg)
                # No longer continuing - we'll raise an exception at the end to trigger rollback

        # Instead of raising an exception, check for errors and manually trigger a rollback if needed
        if errors:
            # Prepare error message
            error_summary = (
                f"Failed to update schedule: {len(errors)} game(s) had errors:\n"
                + "\n".join(errors)
            )
            # Manually roll back the transaction and return error JSON
            transaction.set_rollback(True)
            return JsonResponse({"status": "error", "error": error_summary}, status=400)

        # Only return success if there were no errors (transaction will commit)
        return JsonResponse(
            {
                "status": "success",
                "deleted_count": deleted_count,
                "created_count": created_count,
                "message": f"Successfully updated schedule with {created_count} games.",
            }
        )
    except Exception as e:
        # Catch any other unexpected errors and return as JSON
        transaction.set_rollback(True)
        return JsonResponse(
            {"status": "error", "error": f"Unexpected error: {str(e)}"}, status=500
        )


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
