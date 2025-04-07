from django.shortcuts import render
from django.http import JsonResponse
import json

from django.views.decorators.csrf import ensure_csrf_cookie
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
            schedule_data = data.get("schedule", [])
            config_data = data.get("config", {})

            # Extract levels and teams_per_level from the provided config
            levels = config_data.get("levels", ["A", "B", "C"])
            teams_per_level = config_data.get(
                "teams_per_level", {"A": 6, "B": 6, "C": 6}
            )

            validation_results = {
                "Pairings": {
                    "passed": pairing_tests(schedule_data, levels, teams_per_level),
                    "message": "Teams play the correct number of times based on their level size",
                },
                "Cycle Pairings": {
                    "passed": cycle_pairing_test(
                        schedule_data, levels, teams_per_level
                    ),
                    "message": "Matchups repeat in proper round-robin cycles for each level",
                },
                "Referee-Player": {
                    "passed": referee_player_test(schedule_data),
                    "message": "No team referees a game in which they are playing",
                },
                "Adjacent Slots": {
                    "passed": adjacent_slot_test(schedule_data),
                    "message": "Teams only referee in slots directly adjacent to when they play",
                },
            }

            return JsonResponse(validation_results)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@ensure_csrf_cookie
def get_config(request):
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
                num_cores=1, use_saved_schedule=False, max_attempts=30000
            )

            return JsonResponse({"config": scheduler.config, "schedule": schedule})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
