from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import SavedSchedule
import json
import os
import datetime

# Direct imports from schedule.py
import schedule
from schedule import find_schedule, load_schedule_from_file, save_schedule_to_file

from django.views.decorators.csrf import ensure_csrf_cookie
from tests import (
    pairing_tests,
    cycle_pairing_test,
    referee_player_test,
    adjacent_slot_test,
)


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

            # Get level and team configuration
            # In a real app, you'd get this from your database or settings
            levels = ["A", "B", "C"]  # Example
            teams_per_level = {"A": 6, "B": 6, "C": 6}  # Example

            validation_results = {
                "Pairings": {
                    "passed": pairing_tests(schedule_data, levels, teams_per_level),
                    "message": "Each team plays against every other team exactly once",
                },
                "Cycle Pairings": {
                    "passed": cycle_pairing_test(
                        schedule_data, levels, teams_per_level
                    ),
                    "message": "Teams play in different orders throughout the schedule",
                },
                "Referee-Player": {
                    "passed": referee_player_test(schedule_data),
                    "message": "No team referees a game they are playing in",
                },
                "Adjacent Slots": {
                    "passed": adjacent_slot_test(schedule_data),
                    "message": "Teams referee in slots adjacent to their games",
                },
            }

            return JsonResponse(validation_results)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
