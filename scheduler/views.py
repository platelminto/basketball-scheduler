from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import SavedSchedule
import json
import os
import datetime

# Direct imports from schedule.py
import schedule
from schedule import find_schedule, load_schedule_from_file, save_schedule_to_file


def schedule_viewer(request):
    """View to display the schedule generator interface"""
    return render(request, "scheduler/schedule_viewer.html")


def generate_schedule(request):
    """Generate a new schedule using schedule.py and return it as JSON"""
    try:
        # Directly call the imported function
        schedule_data = find_schedule()

        if not schedule_data:
            return JsonResponse(
                {"success": False, "error": "Failed to generate a valid schedule"}
            )

        # Return the schedule as JSON
        return JsonResponse({"success": True, "schedule": schedule_data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def load_schedule(request):
    """Load a saved schedule from file"""
    try:
        # Directly call the imported function
        schedule_data = load_schedule_from_file()

        if not schedule_data:
            return JsonResponse({"success": False, "error": "No saved schedule found"})

        # Try to load team information
        team_info = {}
        team_info_path = "saved_schedule_teams.json"
        if os.path.exists(team_info_path):
            with open(team_info_path, "r") as f:
                team_info = json.load(f)

        return JsonResponse(
            {"success": True, "schedule": schedule_data, "team_info": team_info}
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def save_schedule_with_times(request):
    """Save a schedule with time information"""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Only POST requests are allowed"}
        )

    try:
        data = json.loads(request.body)
        schedule_data = data.get("schedule")
        team_info = data.get("team_info", {})

        # Save the schedule with time information
        saved_schedule = SavedSchedule(
            name=data.get("name", "Generated Schedule"),
            raw_schedule_data=schedule_data,
            complete_schedule_data=data.get("complete_schedule"),
            start_date=(
                datetime.datetime.strptime(data.get("start_date"), "%Y-%m-%d").date()
                if data.get("start_date")
                else None
            ),
        )
        saved_schedule.save()

        # Use the imported function to save to file
        save_schedule_to_file(schedule_data)

        # Save team information
        with open("saved_schedule_teams.json", "w") as f:
            json.dump(team_info, f, indent=2)

        return JsonResponse({"success": True, "schedule_id": saved_schedule.id})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
