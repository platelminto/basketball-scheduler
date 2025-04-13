from django.shortcuts import render
from django.http import JsonResponse, HttpRequest
import json
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from datetime import datetime
from scheduler.models import Season, Level, Team, Game

from tests import (
    pairing_tests,
    cycle_pairing_test,
    referee_player_test,
    adjacent_slot_test,
)
from utils import get_config_from_schedule_creator


def schedule_viewer(request):
    """Main schedule viewing page"""
    return render(request, "scheduler/schedule_viewer.html")


def create_schedule(request):
    """View to start creating a new schedule"""
    return render(request, "scheduler/create_schedule.html")


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
                num_cores=14, use_saved_schedule=False, max_attempts=30000
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
