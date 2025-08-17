"""
Schedule generation service functions.

This module contains business logic for schedule generation including
threading, cancellation handling, and generation validation.
"""

import threading
from django.core.cache import cache
from utils import get_config_from_schedule_creator


def validate_generation_constraints(schedule, week_data):
    """Validate that generated schedule matches court capacity constraints."""
    seen_off_weeks = 0
    for data_week in week_data.values():
        if data_week.get("isOffWeek", False):
            seen_off_weeks += 1
            continue

        schedule_week = schedule[data_week["week_number"] - 1 - seen_off_weeks]
        schedule_games = [
            game for slot in schedule_week["slots"].values() for game in slot
        ]

        expected_games = len(data_week["games"])
        actual_games = len(schedule_games)

        if expected_games != actual_games:
            raise ValueError(
                f"Court capacity mismatch in week {data_week['week_number']}: "
                f"Expected {expected_games} games based on court availability, "
                f"but schedule generator produced {actual_games} games. "
                f"Please adjust the number of time slots or courts to match the expected game count."
            )


def format_generated_schedule(schedule, week_data):
    """Format the generated schedule to match frontend expectations."""
    scheduled_week_data = []
    seen_off_weeks = 0
    
    for data_week in week_data.values():
        if data_week.get("isOffWeek", False):
            seen_off_weeks += 1
            continue

        schedule_week = schedule[data_week["week_number"] - 1 - seen_off_weeks]
        schedule_games = [
            game for slot in schedule_week["slots"].values() for game in slot
        ]
        week = []

        for i, data_game in enumerate(data_week["games"]):
            schedule_game = schedule_games[i]
            data_game["level_name"] = schedule_game["level"]
            data_game["team1_name"] = schedule_game["teams"][0]
            data_game["team2_name"] = schedule_game["teams"][1]
            data_game["referee_name"] = schedule_game["ref"]
            week.append(data_game)

        scheduled_week_data.append(week)

    return scheduled_week_data


def generate_schedule_async(setup_data, week_data, parameters, session_key):
    """Generate a schedule asynchronously with cancellation support."""
    from schedule import generate_schedule
    
    # Get configuration from the setup data
    config = get_config_from_schedule_creator(setup_data, week_data)

    # Apply parameters from the frontend, with fallbacks to defaults
    config["min_referee_count"] = parameters.get("min_referee_count", 4)
    config["max_referee_count"] = parameters.get("max_referee_count", 6)
    config["slot_limits"] = parameters.get(
        "slot_limits", {1: 3, 2: 5, 3: 5, 4: 4}
    )

    # Convert string keys to integers for slot_limits
    if isinstance(config["slot_limits"], dict):
        config["slot_limits"] = {
            int(k): v for k, v in config["slot_limits"].items()
        }

    # Extract optimization parameters
    time_limit = parameters.get("time_limit", 10.0)
    # If empty it's an empty string, which means the get() succeeds, so we can't just use default
    if not parameters.get("num_blueprints_to_generate"):
        num_blueprints_to_generate = max(1, int(time_limit / 10))
    else:
        num_blueprints_to_generate = int(
            parameters["num_blueprints_to_generate"]
        )
    gap_rel = parameters.get("gapRel", 0.25)

    # Create cancellation event and session key for this generation
    cancellation_key = f"schedule_generation_cancelled_{session_key}"

    # Clear any existing cancellation flag
    cache.delete(cancellation_key)

    # Create thread-safe result container
    result_container = {"schedule": None, "error": None}
    generation_event = threading.Event()

    def generate_in_thread():
        try:
            # Create cancellation checker function
            def is_cancelled():
                return cache.get(cancellation_key, False)

            schedule = generate_schedule(
                config,
                config["team_names_by_level"],
                time_limit=time_limit,
                num_blueprints_to_generate=num_blueprints_to_generate,
                gapRel=gap_rel,
                cancellation_checker=is_cancelled,
            )
            result_container["schedule"] = schedule
        except Exception as e:
            result_container["error"] = e
        finally:
            generation_event.set()

    # Start generation in background thread
    generation_thread = threading.Thread(target=generate_in_thread)
    generation_thread.start()

    # Wait for completion or timeout
    generation_event.wait(timeout=time_limit + 10)  # Add 10 seconds buffer

    # Check if cancelled
    if cache.get(cancellation_key, False):
        raise Exception("Schedule generation was cancelled")

    # Check for error
    if result_container["error"]:
        raise result_container["error"]

    schedule = result_container["schedule"]

    if not schedule:
        raise Exception("No schedule found")

    # Validate that court capacity matches expected games per week
    validate_generation_constraints(schedule, week_data)

    # Format the schedule
    scheduled_week_data = format_generated_schedule(schedule, week_data)

    return {"config": config, "schedule": scheduled_week_data}


def handle_generation_cancellation(session_key):
    """Handle cancellation of ongoing schedule generation."""
    if session_key:
        cancellation_key = f"schedule_generation_cancelled_{session_key}"
        cache.set(cancellation_key, True, timeout=300)  # 5 minute timeout
        return {"message": "Cancellation requested"}
    else:
        raise ValueError("No active session")