"""
Schedule generation service functions.

This module contains business logic for schedule generation including
threading, cancellation handling, and generation validation.
"""

import copy
import multiprocessing
import random

from django.core.cache import cache
from utils import get_config_from_schedule_creator


DEFAULT_TIME_PER_BLUEPRINT = 6
MAX_NUM_BLUEPRINTS = 100


def generate_schedule_process(courts_per_slot, team_names_by_level, time_limit, num_blueprints_to_generate, gap_rel, 
                             progress_key, shared_dict, session_key, week_data):
    """Function that runs in a separate process for schedule generation."""
    try:
        # Import here to avoid Django issues in subprocess
        from schedule import generate_schedule
        
        # Create cancellation checker function using persistent files
        def is_cancelled():
            import os
            from django.conf import settings
            cancel_file = os.path.join(settings.BASE_DIR, "tmp", f"schedule_cancel_{session_key}")
            return os.path.exists(cancel_file)
        

        # Create simple progress callback that just stores data without formatting
        def update_progress(progress_data):
            # Write to file for cross-process communication using atomic write
            import tempfile
            import os
            import json
            progress_file = os.path.join(tempfile.gettempdir(), f"{progress_key}.json")
            try:
                # Write to temporary file first, then rename (atomic operation)
                temp_file = progress_file + ".tmp"
                with open(temp_file, 'w') as f:
                    json.dump(progress_data, f)
                os.rename(temp_file, progress_file)
            except Exception as e:
                print(f"Error writing progress file: {e}")
                # Clean up temp file if it exists
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            # Also store best data in shared dict (unformatted)
            if 'best_score' in progress_data and progress_data['best_score'] is not None:
                shared_dict['best_score'] = progress_data['best_score']
                shared_dict['best_possible_score'] = progress_data.get('best_possible_score')
            # Store best schedule if provided (unformatted - will be formatted when needed)
            if 'best_schedule' in progress_data and progress_data['best_schedule'] is not None:
                shared_dict['best_schedule'] = progress_data['best_schedule']
        
        # randomise teams within each level
        randomized_team_names_by_level = {}
        for level, teams in team_names_by_level.items():
            randomized_teams = teams.copy()
            random.shuffle(randomized_teams)
            randomized_team_names_by_level[level] = randomized_teams
        

        schedule = generate_schedule(
            courts_per_slot,
            randomized_team_names_by_level,
            time_limit=time_limit,
            num_blueprints_to_generate=num_blueprints_to_generate,
            gapRel=gap_rel,
            cancellation_checker=is_cancelled,
            use_best_checker=None,
            progress_callback=update_progress,
        )
        
        # Store final result in shared dict
        shared_dict['schedule'] = schedule
        shared_dict['error'] = None
        
    except Exception as e:
        import traceback
        shared_dict['schedule'] = None
        shared_dict['error'] = traceback.format_exc()
    finally:
        # Clean up progress data when done
        cache.delete(progress_key)
        # Note: We intentionally don't delete the progress file here
        # so that the frontend can do a final poll to get the last blueprint results
        # The progress file will be cleaned up on the next generation


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
    
    # Store week_data in cache so progress endpoint can access it for formatting
    week_data_key = f"schedule_generation_week_data_{session_key}"
    cache.set(week_data_key, week_data, timeout=300)
    
    # Extract needed data directly instead of using config
    from utils import get_config_from_schedule_creator
    temp_config = get_config_from_schedule_creator(setup_data, week_data)
    
    courts_per_slot = temp_config["courts_per_slot"]
    team_names_by_level = temp_config["team_names_by_level"]

    # Apply parameters from the frontend - these are no longer used by the scheduler
    # but kept for potential future use or backwards compatibility

    # Extract optimization parameters
    time_limit = parameters.get("time_limit", 10.0)
    # If empty it's an empty string, which means the get() succeeds, so we can't just use default
    if not parameters.get("num_blueprints_to_generate"):
        num_blueprints_to_generate = min(max(1, int(time_limit / DEFAULT_TIME_PER_BLUEPRINT)), MAX_NUM_BLUEPRINTS)
    else:
        num_blueprints_to_generate = int(
            parameters["num_blueprints_to_generate"]
        )
    gap_rel = parameters.get("gapRel", 0.01)

    # Create progress key for this generation
    progress_key = f"schedule_generation_progress_{session_key}"

    # Clear any existing progress data and cancel files
    cache.delete(progress_key)
    
    # Clean up any leftover cancel files from previous generations
    import os
    from django.conf import settings
    tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    cancel_file = os.path.join(tmp_dir, f"schedule_cancel_{session_key}")
    
    try:
        if os.path.exists(cancel_file):
            os.remove(cancel_file)
    except Exception as e:
        print(f"Error cleaning up cancel file: {e}")
    
    # Clean up any leftover progress files from previous generations
    import tempfile
    import os
    progress_file = os.path.join(tempfile.gettempdir(), f"{progress_key}.json")
    
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        print(f"Error cleaning up progress file {progress_file}: {e}")

    # Create multiprocessing manager for shared state
    manager = multiprocessing.Manager()
    shared_dict = manager.dict()
    shared_dict['schedule'] = None
    shared_dict['error'] = None
    shared_dict['best_score'] = None
    shared_dict['best_possible_score'] = None
    shared_dict['best_schedule'] = None

    # Create and start the generation process
    generation_process = multiprocessing.Process(
        target=generate_schedule_process,
        args=(courts_per_slot, team_names_by_level, time_limit, num_blueprints_to_generate, gap_rel,
              progress_key, shared_dict, session_key, week_data)
    )
    generation_process.start()
    
    # Store process info in cache for cancellation
    process_key = f"schedule_generation_process_{session_key}"
    cache.set(process_key, generation_process.pid, timeout=300)

    # Wait for completion (no timeout - let it finish naturally or be cancelled by user)
    generation_process.join()

    # Clean up process cache entry and week_data
    cache.delete(process_key)
    week_data_key = f"schedule_generation_week_data_{session_key}"
    cache.delete(week_data_key)
    
    # Small delay to allow any pending cancellation requests to be processed
    # (race condition: user clicks cancel right as process finishes)
    import time
    time.sleep(0.1)
    
    # Check if process was killed/terminated (indicating cancellation)
    process_was_killed = generation_process.exitcode is not None and generation_process.exitcode != 0
    
    # Check cancellation status from files
    import os
    from django.conf import settings
    cancel_file = os.path.join(settings.BASE_DIR, "tmp", f"schedule_cancel_{session_key}")
    was_cancelled = os.path.exists(cancel_file)
    
    # If process was killed externally (likely by cancellation), treat as cancelled
    if process_was_killed and not was_cancelled:
        was_cancelled = True
    
    # Check if process is still running (timeout or cancellation)
    if generation_process.is_alive():
        generation_process.terminate()  # Force kill if still running
        generation_process.join(timeout=1)  # Give it a second to clean up
        if generation_process.is_alive():
            generation_process.kill()  # Nuclear option
    
    # Check if cancelled (complete cancellation should return a specific response, not error)
    if was_cancelled:
        # Clean up progress file and cancel file on cancellation
        import tempfile
        progress_file = os.path.join(tempfile.gettempdir(), f"{progress_key}.json")
        try:
            if os.path.exists(progress_file):
                os.remove(progress_file)
            if os.path.exists(cancel_file):
                os.remove(cancel_file)
        except Exception as e:
            print(f"Error cleaning up files on cancellation: {e}")
        return {"message": "Schedule generation was cancelled"}
    
    # Normal completion case - check for error and schedule
    if shared_dict.get("error"):
        raise Exception(shared_dict["error"])

    schedule = shared_dict.get("schedule")

    if not schedule:
        # Before throwing error, check one more time if cancellation was requested
        # (race condition: cancellation might come in after the initial check)
        final_cancel_check = os.path.exists(cancel_file)
        if final_cancel_check:
            try:
                if os.path.exists(cancel_file):
                    os.remove(cancel_file)
            except:
                pass
            return {"message": "Schedule generation was cancelled"}
        else:
            raise Exception("No schedule found")

    # Validate that court capacity matches expected games per week
    validate_generation_constraints(schedule, week_data)

    # Format the schedule
    scheduled_week_data = format_generated_schedule(schedule, week_data)

    # Get final progress data (including all blueprint_results) to include in response
    final_progress = get_generation_progress(session_key)
    blueprint_results = final_progress.get('blueprint_results', {}) if final_progress else {}

    return {
        "schedule": scheduled_week_data,
        "blueprint_results": blueprint_results
    }


def handle_generation_cancellation(session_key):
    """Handle cancellation of ongoing schedule generation.
    
    Args:
        session_key: The session key
    """
    if session_key:
        progress_key = f"schedule_generation_progress_{session_key}"
        process_key = f"schedule_generation_process_{session_key}"
        
        # Create cancellation flag file
        import os
        from django.conf import settings
        tmp_dir = os.path.join(settings.BASE_DIR, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        
        cancel_file = os.path.join(tmp_dir, f"schedule_cancel_{session_key}")
        try:
            with open(cancel_file, 'w') as f:
                f.write('1')
        except Exception as e:
            print(f"Error creating cancel file: {e}")
        
        # Get the process ID if it exists
        process_pid = cache.get(process_key)
        
        if process_pid:
            try:
                import psutil
                process = psutil.Process(process_pid)
                process.terminate()  # Send SIGTERM
                try:
                    process.wait(timeout=1)  # Wait up to 1 second for graceful shutdown
                except psutil.TimeoutExpired:
                    process.kill()  # Send SIGKILL if it doesn't respond
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ProcessLookupError):
                print(f"Process {process_pid} already terminated")
            except Exception as e:
                print(f"Error killing process {process_pid}: {e}")
        
        # The main generation function will detect the process death and treat it as cancellation
        message = "Generation cancelled"
            
        # Clean up cache entries
        cache.delete(process_key)
        cache.delete(progress_key)
        
        return {"message": message}
    else:
        raise ValueError("No active session")


def get_generation_progress(session_key):
    """Get the current progress of schedule generation."""
    if session_key:
        progress_key = f"schedule_generation_progress_{session_key}"
        
        # Try to read from file first (for cross-process communication)
        import tempfile
        import os
        import json
        progress_file = os.path.join(tempfile.gettempdir(), f"{progress_key}.json")
        
        try:
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                return progress_data
        except Exception as e:
            print(f"Error reading progress file: {e}")
        
        # Fallback to cache (shouldn't work with multiprocessing but keeping it)
        progress_data = cache.get(progress_key)
        if progress_data:
            return json.loads(progress_data)
        else:
            return None
    else:
        raise ValueError("No active session")