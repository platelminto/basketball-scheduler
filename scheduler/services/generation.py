"""
Schedule generation service functions.

This module contains business logic for schedule generation including
threading, cancellation handling, and generation validation.
"""

import multiprocessing
import json
import os
import signal
from django.core.cache import cache
from utils import get_config_from_schedule_creator


def generate_schedule_process(config, time_limit, num_blueprints_to_generate, gap_rel, 
                             cancellation_key, use_best_key, progress_key, shared_dict, session_key):
    """Function that runs in a separate process for schedule generation."""
    try:
        # Import here to avoid Django issues in subprocess
        from schedule import generate_schedule
        
        # Create cancellation checker function using file (since cache doesn't work across processes)
        def is_cancelled():
            import tempfile
            import os
            cancel_file = os.path.join(tempfile.gettempdir(), f"{cancellation_key}.flag")
            return os.path.exists(cancel_file)
        
        # Create use_best checker function using file
        def is_use_best():
            import tempfile
            import os
            use_best_file = os.path.join(tempfile.gettempdir(), f"{use_best_key}.flag")
            return os.path.exists(use_best_file)
        

        # Create simple progress callback that just stores data without formatting
        def update_progress(progress_data):
            # Write to file for cross-process communication
            import tempfile
            import os
            import json
            progress_file = os.path.join(tempfile.gettempdir(), f"{progress_key}.json")
            try:
                with open(progress_file, 'w') as f:
                    json.dump(progress_data, f)
            except Exception as e:
                print(f"Error writing progress file: {e}")
            
            # Also store best data in shared dict (unformatted)
            if 'best_score' in progress_data and progress_data['best_score'] is not None:
                shared_dict['best_score'] = progress_data['best_score']
                shared_dict['best_possible_score'] = progress_data.get('best_possible_score')
            # Store best schedule if provided (unformatted - will be formatted when needed)
            if 'best_schedule' in progress_data and progress_data['best_schedule'] is not None:
                shared_dict['best_schedule'] = progress_data['best_schedule']
        
        schedule = generate_schedule(
            config,
            config["team_names_by_level"],
            time_limit=time_limit,
            num_blueprints_to_generate=num_blueprints_to_generate,
            gapRel=gap_rel,
            cancellation_checker=is_cancelled,
            use_best_checker=is_use_best,
            progress_callback=update_progress,
        )
        
        # Store final result in shared dict
        shared_dict['schedule'] = schedule
        shared_dict['error'] = None
        
    except Exception as e:
        shared_dict['schedule'] = None
        shared_dict['error'] = str(e)
    finally:
        # Clean up progress data when done
        cache.delete(progress_key)
        # Also clean up progress file
        import tempfile
        import os
        progress_file = os.path.join(tempfile.gettempdir(), f"{progress_key}.json")
        try:
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except Exception as e:
            print(f"Error cleaning up progress file: {e}")


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
    import json
    
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
    use_best_key = f"schedule_generation_use_best_{session_key}"
    progress_key = f"schedule_generation_progress_{session_key}"

    # Clear any existing flags and progress data
    cache.delete(cancellation_key)
    cache.delete(use_best_key)
    cache.delete(progress_key)

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
        args=(config, time_limit, num_blueprints_to_generate, gap_rel,
              cancellation_key, use_best_key, progress_key, shared_dict, session_key)
    )
    generation_process.start()
    
    # Store process info in cache for cancellation
    process_key = f"schedule_generation_process_{session_key}"
    cache.set(process_key, generation_process.pid, timeout=300)

    # Wait for completion or timeout
    generation_process.join(timeout=time_limit + 10)  # Add 10 seconds buffer

    # Clean up process cache entry
    cache.delete(process_key)
    
    # Small delay to allow any pending cancellation requests to be processed
    # (race condition: user clicks cancel right as process finishes)
    import time
    time.sleep(0.1)
    
    # Check if process was killed/terminated (indicating cancellation)
    process_was_killed = generation_process.exitcode is not None and generation_process.exitcode != 0
    
    # Check cancellation status first (both cache and file, due to race conditions)
    was_cancelled = cache.get(cancellation_key, False)
    use_best_requested = cache.get(use_best_key, False)
    
    # Also check file-based flags (in case cache hasn't been set yet due to timing)
    import tempfile
    import os
    cancel_file = os.path.join(tempfile.gettempdir(), f"{cancellation_key}.flag")
    use_best_file = os.path.join(tempfile.gettempdir(), f"{use_best_key}.flag")
    
    file_cancelled = os.path.exists(cancel_file)
    file_use_best = os.path.exists(use_best_file)
    
    # Use either source
    was_cancelled = was_cancelled or file_cancelled
    use_best_requested = use_best_requested or file_use_best
    
    # If process was killed externally (likely by cancellation), treat as cancelled
    if process_was_killed and not was_cancelled and not use_best_requested:
        was_cancelled = True
    
    # Check if process is still running (timeout or cancellation)
    if generation_process.is_alive():
        generation_process.terminate()  # Force kill if still running
        generation_process.join(timeout=1)  # Give it a second to clean up
        if generation_process.is_alive():
            generation_process.kill()  # Nuclear option
    
    # Check if cancelled (complete cancellation should return a specific response, not error)
    if was_cancelled:
        cache.delete(cancellation_key)
        # Clean up progress file on cancellation
        import tempfile
        import os
        progress_file = os.path.join(tempfile.gettempdir(), f"{progress_key}.json")
        try:
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except Exception as e:
            print(f"Error cleaning up progress file on cancellation: {e}")
        return {"message": "Schedule generation was cancelled"}
    
    # Check if "use best" was requested - this is not an error, just early termination
    if use_best_requested:
        cache.delete(use_best_key)
        # Return the best schedule found so far from shared state
        best_schedule = shared_dict.get('best_schedule')
        if best_schedule is not None:
            # We have a best schedule, use it as the final result
            schedule = best_schedule
            # Continue to formatting and validation below
        else:
            return {"message": "Use best requested but no valid schedule found yet"}
    else:
        # Normal completion case - check for error and schedule
        
        if shared_dict.get("error"):
            raise Exception(shared_dict["error"])

        schedule = shared_dict.get("schedule")

        if not schedule:
            # Before throwing error, check one more time if cancellation was requested
            # (race condition: cancellation might come in after the initial check)
            final_cancel_check = cache.get(cancellation_key, False)
            final_use_best_check = cache.get(use_best_key, False)
            if final_cancel_check:
                cache.delete(cancellation_key)
                return {"message": "Schedule generation was cancelled"}
            elif final_use_best_check:
                cache.delete(use_best_key)
                return {"message": "Use best requested but no valid schedule found yet"}
            else:
                raise Exception("No schedule found")

    # Validate that court capacity matches expected games per week
    validate_generation_constraints(schedule, week_data)

    # Format the schedule
    scheduled_week_data = format_generated_schedule(schedule, week_data)

    return {"config": config, "schedule": scheduled_week_data}


def handle_generation_cancellation(session_key, use_best=False):
    """Handle cancellation of ongoing schedule generation.
    
    Args:
        session_key: The session key  
        use_best: If True, stop generation but return best schedule found so far
    """
    if session_key:
        cancellation_key = f"schedule_generation_cancelled_{session_key}"
        use_best_key = f"schedule_generation_use_best_{session_key}"
        progress_key = f"schedule_generation_progress_{session_key}"
        process_key = f"schedule_generation_process_{session_key}"
        
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
        
        # Set the appropriate flag for the return logic using files (for cross-process communication)
        import tempfile
        import os
        if use_best:
            cache.set(use_best_key, True, timeout=300)
            # Also create file for subprocess
            use_best_file = os.path.join(tempfile.gettempdir(), f"{use_best_key}.flag")
            try:
                with open(use_best_file, 'w') as f:
                    f.write('1')
            except Exception as e:
                print(f"Error creating use_best flag file: {e}")
            message = "Generation stopped, using best schedule found"
            
            # Get the current progress to find the best schedule
            progress_data = cache.get(progress_key)
            if progress_data and progress_data.get('best_schedule'):
                # Convert the best_schedule to the format expected by the frontend
                best_schedule = progress_data['best_schedule']
                
                # Convert from progressData format to the format expected by apply function
                converted_schedule = []
                for week_data in best_schedule:
                    # week_data is { week: 1, slots: { 1: [games], 2: [games], ... } }
                    all_games_for_week = []
                    
                    # Flatten all games from all slots into a single array
                    for slot_games in week_data['slots'].values():
                        if isinstance(slot_games, list):
                            all_games_for_week.extend(slot_games)
                    
                    converted_schedule.append(all_games_for_week)
                
                # Clean up cache entries and flag files first
                cache.delete(process_key)
                cache.delete(progress_key)
                
                return {
                    "message": message,
                    "schedule": converted_schedule
                }
        else:
            cache.set(cancellation_key, True, timeout=300)
            # Also create file for subprocess
            cancel_file = os.path.join(tempfile.gettempdir(), f"{cancellation_key}.flag")
            try:
                with open(cancel_file, 'w') as f:
                    f.write('1')
            except Exception as e:
                print(f"Error creating cancellation flag file: {e}")
            message = "Generation cancelled"
            
        # Clean up cache entries and flag files
        cache.delete(process_key)
        cache.delete(progress_key)
        
        # Clean up flag files
        try:
            cancel_file = os.path.join(tempfile.gettempdir(), f"{cancellation_key}.flag")
            if os.path.exists(cancel_file):
                os.remove(cancel_file)
            use_best_file = os.path.join(tempfile.gettempdir(), f"{use_best_key}.flag")
            if os.path.exists(use_best_file):
                os.remove(use_best_file)
        except Exception as e:
            print(f"Error cleaning up flag files: {e}")
        
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