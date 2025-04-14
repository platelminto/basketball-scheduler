from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest
import json
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction, IntegrityError
from datetime import datetime
from scheduler.models import Season, Level, Team, Game
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


@csrf_exempt
@require_POST
@transaction.atomic
def save_schedule(request: HttpRequest):
    """
    Receives schedule data via POST, creates/updates Season, Level, Team, Game objects.
    Replaces existing data for a Season if the name matches.
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
        # Get or create the season. If it exists, delete its children first.
        season, created = Season.objects.get_or_create(name=season_name)
        if not created:
            # If season already existed, clear its previous levels, teams, and games
            # Cascading delete handles Teams and Games when Level is deleted
            season.levels.all().delete()
            # Re-fetch the season instance after potential deletion side-effects if needed,
            # though get_or_create should return the correct instance.

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

        # --- 3. Create Games ---
        created_games_count = 0
        errors = []
        for assignment in game_assignments:
            level_name = assignment.get("level")
            team1_name = assignment.get("team1")
            team2_name = assignment.get("team2")
            ref_name = assignment.get("referee")
            week = assignment.get("week")
            date_str = assignment.get("date")
            time_str = assignment.get("time")
            court_name = assignment.get("court")  # Assuming court name is passed

            # Validate basic data presence
            if not all(
                [level_name, team1_name, team2_name, ref_name, week is not None]
            ):
                errors.append(f"Skipping game due to missing data: {assignment}")
                continue

            # Find corresponding model instances
            level_obj = level_instances.get(level_name)
            if not level_obj:
                errors.append(
                    f"Skipping game: Level '{level_name}' not found for assignment: {assignment}"
                )
                continue

            team1_obj = team_instances.get(level_name, {}).get(team1_name)
            team2_obj = team_instances.get(level_name, {}).get(team2_name)
            ref_obj = team_instances.get(level_name, {}).get(ref_name)

            if not all([team1_obj, team2_obj, ref_obj]):
                errors.append(
                    f"Skipping game: One or more teams ('{team1_name}', '{team2_name}', Ref: '{ref_name}') not found in level '{level_name}' for assignment: {assignment}"
                )
                continue

            # Combine date and time
            game_datetime = None
            if date_str and time_str:
                try:
                    # Assuming YYYY-MM-DD and HH:MM format from the frontend
                    game_datetime = datetime.strptime(
                        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    errors.append(
                        f"Skipping game: Invalid date/time format ('{date_str} {time_str}') for assignment: {assignment}"
                    )
                    continue  # Skip if date/time format is wrong

            try:
                Game.objects.create(
                    level=level_obj,
                    week=week,
                    team1=team1_obj,
                    team2=team2_obj,
                    referee_team=ref_obj,
                    date_time=game_datetime,
                    court=court_name,
                )
                created_games_count += 1
            except IntegrityError as e:
                errors.append(
                    f"Database error creating game for assignment {assignment}: {e}"
                )
            except Exception as e:  # Catch other potential errors during game creation
                errors.append(
                    f"Unexpected error creating game for assignment {assignment}: {e}"
                )

        if errors:
            return JsonResponse(
                {
                    "status": "warning",
                    "message": f"Schedule partially saved for season '{season_name}' with {len(errors)} errors.",
                    "season_id": season.id,
                    "games_created": created_games_count,
                    "errors": errors,
                },
                status=207,
            )  # Multi-Status response

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
        .select_related("level", "team1", "team2", "referee_team")
        .order_by("week", "date_time", "level__name")
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

    # Group games by week number
    games_by_week = defaultdict(list)
    for game in games:
        games_by_week[game.week].append(game)

    context = {
        "season": season,
        "games_by_week": dict(games_by_week),
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
        "level", "team1", "team2", "referee_team"
    )

    game_data = []
    for game in games:
        # Format datetime consistently for comparison (ISO format without timezone)
        datetime_str = (
            game.date_time.strftime("%Y-%m-%dT%H:%M") if game.date_time else None
        )
        game_data.append(
            {
                "id": str(game.id),  # Use string IDs for consistency with JS
                "datetime": datetime_str,
                "court": game.court or "",  # Ensure consistent type (string)
                "level": str(game.level_id),
                "team1": str(game.team1_id),
                "team2": str(game.team2_id),
                "referee": str(game.referee_team_id) if game.referee_team else "",
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
    """
    # Basic permission check (enhance as needed)
    # if not request.user.is_staff:
    #     return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        data = json.loads(request.body)
        new_games_data = data.get("games", [])
        if not isinstance(new_games_data, list):
            raise ValueError("'games' data must be a list.")
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"error": f"Invalid JSON or data format: {e}"}, status=400)

    # --- 1. Get Season and related data ---
    season = get_object_or_404(Season, pk=season_id)
    # Fetch valid levels and teams for this season ONCE for efficient lookup
    valid_levels = {
        str(level.id): level for level in Level.objects.filter(season=season)
    }
    valid_teams = {
        str(team.id): team for team in Team.objects.filter(level__season=season)
    }

    # --- 2. Delete existing games for this season ---
    # Note: This assumes Levels and Teams are NOT deleted/recreated here, only Games.
    deleted_count, _ = Game.objects.filter(level__season=season).delete()
    # Log deletion if desired: print(f"Deleted {deleted_count} existing games for season {season_id}")

    # --- 3. Create new games from payload ---
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
            datetime_str = game_data.get("datetime")  # Can be None or ""
            court = game_data.get("court")  # Can be None or ""
            score1_str = game_data.get("score1")  # Can be None or ""
            score2_str = game_data.get("score2")  # Can be None or ""

            # --- Basic Validation ---
            if not all([week_str, level_id_str, team1_id_str, team2_id_str]):
                raise ValueError("Missing required fields (week, level, team1, team2)")

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

            referee_obj = None
            if referee_id_str:  # Only look up if provided
                referee_obj = valid_teams.get(str(referee_id_str))
                if not referee_obj or referee_obj.level_id != level_obj.id:
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
                week = int(week_str)
                if week <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(f"Invalid week number: {week_str}")

            # --- Parse DateTime ---
            game_datetime = None
            if datetime_str:
                parsed_dt = parse_datetime(
                    datetime_str
                )  # Handles ISO format like "YYYY-MM-DDTHH:MM"
                if parsed_dt:
                    if settings.USE_TZ:
                        game_datetime = make_aware(parsed_dt, get_current_timezone())
                    else:
                        game_datetime = parsed_dt
                else:
                    raise ValueError(f"Invalid datetime format: {datetime_str}")

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
                week=week,
                team1=team1_obj,
                team2=team2_obj,
                referee_team=referee_obj,  # Assign None if not found/provided
                date_time=game_datetime,
                court=court or None,  # Ensure empty string becomes None
                team1_score=team1_score,
                team2_score=team2_score,
            )
            created_count += 1

        except (ValueError, IntegrityError, TypeError) as e:
            # Catch validation errors, potential DB errors, or type errors
            errors.append(
                f"Error processing game at index {idx}: {e} | Data: {game_data}"
            )
        except Exception as e:  # Catch unexpected errors
            errors.append(
                f"Unexpected error processing game at index {idx}: {e} | Data: {game_data}"
            )

    # --- 4. Return Response ---
    if errors:
        # If any errors occurred, report them (transaction will rollback)
        return JsonResponse(
            {
                "error": "Failed to update schedule due to errors.",
                "details": errors,
                "created_count": created_count,
                "deleted_count": deleted_count,  # Include deleted count for context
            },
            status=400,  # Bad request due to data errors
        )
    else:
        # Success
        return JsonResponse(
            {
                "message": f"Schedule for season {season_id} updated successfully.",
                "created_count": created_count,
                "deleted_count": deleted_count,
            },
            status=200,
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
