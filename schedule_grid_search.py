import json
import time
import itertools
import random
import math
import copy
from datetime import datetime
from multiprocessing import Pool, cpu_count
from schedule import (
    find_schedule_attempt,
    balance_schedule,
    validate_schedule,
    levels,
    teams,
    config,
    compute_team_play_counts,
    compute_overall_ref_counts,
    composite_objective,
    rr_pairings,
    first_half_weeks,
    solve_half_schedule,
    solve_second_half,
)

# Global variables to hold current parameter set
current_params = {}


# Module level function that can be pickled
def attempt_with_current_params():
    """Find schedule attempt with current parameter settings"""
    # Solve first half
    first_half_schedule, first_half_ref_counts = solve_half_schedule(
        rr_pairings, first_half_weeks
    )
    if first_half_schedule is None:
        return None

    second_half_schedule, second_half_ref_counts = solve_second_half(
        rr_pairings, first_half_schedule, first_half_ref_counts
    )
    if second_half_schedule is None:
        return None

    full_schedule = first_half_schedule + second_half_schedule

    # Use custom parameters in balance_schedule
    final_schedule = balance_schedule(
        full_schedule,
        max_iterations=current_params["max_iterations"],
        weight_play=current_params["weight_play"],
        weight_ref=current_params["weight_ref"],
        cooling_rate=current_params["cooling_rate"],
        initial_temp=current_params["initial_temp"],
        candidate_prob=current_params["candidate_prob"],
        swap_prob=current_params["swap_prob"],
    )

    # Validate the schedule
    is_valid, _ = validate_schedule(final_schedule, teams, levels)
    if is_valid:
        return final_schedule
    return None


def grid_search_schedule_params(
    output_file="grid_search_results.json", trials_per_combo=20, max_attempts=1000
):
    """
    Simple grid search over schedule optimization parameters to find optimal settings.

    For each combination, runs multiple trials and records the average attempts needed.

    Args:
        output_file: File to save results
        trials_per_combo: Number of trials per parameter combination
        max_attempts: Maximum attempts per trial before giving up
    """
    global current_params

    # Parameters to search over
    param_grid = {
        # Move type probabilities (candidate vs swap)
        "move_probs": [
            (1.0, 0.0),  # 100% candidate, 0% swap
        ],
        # Cooling rates for simulated annealing
        "cooling_rates": [0.9],
        # Initial temperatures for simulated annealing
        "initial_temps": [5.0],
        # Weight ratios (weight_play, weight_ref)
        "weight_ratios": [
            (0.1, 10.0),  # Heavily favor referee balance
        ],
        # Violation penalty in weighted_play_imbalance_metric
        "violation_penalties": [1e6],
        # Priority multiplier in weighted_play_imbalance_metric
        "priority_multipliers": [100],
        # Max iterations for balance_schedule
        "max_iterations_values": [100, 250, 500, 1000],
    }

    # Calculate total number of combinations
    total_combinations = (
        len(param_grid["move_probs"])
        * len(param_grid["cooling_rates"])
        * len(param_grid["initial_temps"])
        * len(param_grid["weight_ratios"])
        * len(param_grid["violation_penalties"])
        * len(param_grid["priority_multipliers"])
        * len(param_grid["max_iterations_values"])
    )

    print(f"Starting grid search with {total_combinations} parameter combinations")
    print(f"Each combination will be tested {trials_per_combo} times")
    print(f"Maximum attempts per trial: {max_attempts}")
    print(f"Total maximum trials: {total_combinations * trials_per_combo}")

    # Generate all parameter combinations
    all_combinations = []

    # Generate all the combinations from the grid
    for (
        move_prob,
        cooling_rate,
        initial_temp,
        weight_ratio,
        violation_penalty,
        priority_multiplier,
        max_iterations,
    ) in itertools.product(
        param_grid["move_probs"],
        param_grid["cooling_rates"],
        param_grid["initial_temps"],
        param_grid["weight_ratios"],
        param_grid["violation_penalties"],
        param_grid["priority_multipliers"],
        param_grid["max_iterations_values"],
    ):
        combo = {
            "candidate_prob": move_prob[0],
            "swap_prob": move_prob[1],
            "cooling_rate": cooling_rate,
            "initial_temp": initial_temp,
            "weight_play": weight_ratio[0],
            "weight_ref": weight_ratio[1],
            "violation_penalty": violation_penalty,
            "priority_multiplier": priority_multiplier,
            "max_iterations": max_iterations,
        }

        all_combinations.append(combo)

    # Update total for reporting
    total_combinations = len(all_combinations)
    total_trials = total_combinations * trials_per_combo
    print(f"Total of {total_combinations} unique parameter combinations to test")

    # Results storage
    results = []

    # Save original functions to restore later
    original_find_schedule_attempt = find_schedule_attempt
    original_priority_multiplier = config["priority_multiplier"]

    # Process combinations
    batch_size = 20  # Report every 10 trials
    batch_results = []

    # Track total progress
    trial_count = 0

    try:
        for combo_idx, combo in enumerate(all_combinations):
            # Define custom weighted_play_imbalance_metric for this combination
            def custom_weighted_play_imbalance_metric(schedule):
                """Modified version with custom violation penalty"""
                play_counts = compute_team_play_counts(schedule)
                total = 0.0
                violation_penalty = combo["violation_penalty"]

                for level in levels:
                    for t in teams[level]:
                        for s in range(1, config["num_slots"] + 1):
                            count = play_counts[level][t][s]
                            limit = config["slot_limits"].get(s, float("inf"))

                            if count > limit:
                                if s in config["priority_slots"]:
                                    total += (
                                        violation_penalty
                                        * combo["priority_multiplier"]
                                        * (count - limit) ** 2
                                    )
                                else:
                                    total += violation_penalty * (count - limit) ** 2
                return total

            # Update the module-level parameters
            current_params = combo.copy()
            config["priority_multiplier"] = combo["priority_multiplier"]

            # Set up the weighted_play_imbalance_metric function in globals
            globals()[
                "weighted_play_imbalance_metric"
            ] = custom_weighted_play_imbalance_metric

            # Run trials for this combination
            for trial in range(trials_per_combo):
                trial_count += 1
                start_time = time.time()

                print(
                    f"Trial {trial_count}/{total_trials}: Testing combination {combo_idx+1}/{total_combinations}, trial {trial+1}/{trials_per_combo}"
                )

                # Try to find a schedule using parallel processing
                attempts = 0
                schedule = None

                # Get number of cores
                num_cores = 18

                # Parallel approach
                if num_cores > 1:
                    attempts_per_batch = num_cores
                    for attempt in range(0, max_attempts, attempts_per_batch):
                        with Pool(num_cores) as pool:
                            # Create multiple attempts in parallel
                            schedules = pool.starmap(
                                attempt_with_current_params, [()] * attempts_per_batch
                            )

                            # Check if any worked
                            attempts += attempts_per_batch
                            for schedule_result in schedules:
                                if schedule_result is not None:
                                    schedule = schedule_result
                                    break

                            if schedule is not None:
                                break

                            # Break if we've exceeded max attempts
                            if attempts >= max_attempts:
                                break
                else:
                    # Single core fallback
                    for attempt in range(max_attempts):
                        attempts += 1
                        schedule = attempt_with_current_params()
                        if schedule is not None:
                            break

                        # Print progress every few attempts
                        if attempt > 0 and attempt % 10 == 0:
                            print(f"  Attempted {attempt} schedules...")

                end_time = time.time()
                duration = end_time - start_time

                # Record the result
                result = {
                    "params": combo,
                    "trial": trial,
                    "attempts": attempts,
                    "success": schedule is not None,
                    "duration": duration,
                }

                results.append(result)
                batch_results.append(result)

                print(
                    f"Result: {'Success' if result['success'] else 'Failure'} in {result['attempts']} attempts ({duration:.2f}s)"
                )

                # After each batch, report the fastest success
                if len(batch_results) >= batch_size or (
                    combo_idx == len(all_combinations) - 1
                    and trial == trials_per_combo - 1
                ):
                    successful_results = [r for r in batch_results if r["success"]]
                    if successful_results:
                        fastest = min(successful_results, key=lambda r: r["attempts"])
                        print(
                            f"\nFastest in last {len(batch_results)} trials: {fastest['attempts']} attempts with parameters:"
                        )
                        for key, value in fastest["params"].items():
                            print(f"  {key}: {value}")
                    else:
                        print(
                            f"\nNo successful trials in last {len(batch_results)} trials"
                        )

                    # Reset batch results
                    batch_results = []

                    # Periodically save results
                    with open(output_file, "w") as f:
                        json.dump(results, f, indent=2)

                    print(
                        f"Progress: {trial_count}/{total_trials} trials ({trial_count/total_trials*100:.1f}%)\n"
                    )

    finally:
        # Restore original function and config
        globals()["find_schedule_attempt"] = original_find_schedule_attempt
        if "weighted_play_imbalance_metric" in globals():
            del globals()["weighted_play_imbalance_metric"]
        config["priority_multiplier"] = original_priority_multiplier

    # Final save
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Compute summary statistics (modified to count failures as max_attempts)
    summary = {}
    for combo_idx, combo in enumerate(all_combinations):
        combo_key = f"combo_{combo_idx}"
        combo_results = [r for r in results if r["params"] == combo]

        # Calculate success rate
        successful_trials = [r for r in combo_results if r["success"]]
        success_rate = (
            len(successful_trials) / len(combo_results) if combo_results else 0
        )

        # Calculate attempt statistics - COUNT FAILURES AS MAX_ATTEMPTS
        attempts = []
        for trial in combo_results:
            if trial["success"]:
                attempts.append(trial["attempts"])
            else:
                attempts.append(max_attempts)  # Count failures as max_attempts

        avg_attempts = sum(attempts) / len(attempts) if attempts else 0
        min_attempts = min(attempts) if attempts else 0
        max_attempts_actual = max(attempts) if attempts else 0

        summary[combo_key] = {
            "params": combo,
            "success_rate": success_rate,
            "avg_attempts": avg_attempts,
            "min_attempts": min_attempts,
            "max_attempts": max_attempts_actual,
            "raw_attempts": attempts,  # Store the modified attempts that include max for failures
            "durations": [r["duration"] for r in combo_results],
        }

    # Save summary
    summary_file = output_file.replace(".json", "_summary.json")
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Find best parameters - considers both success rate and avg_attempts now
    best_combo = None
    best_score = float("inf")

    for combo_key, stats in summary.items():
        # Only consider combinations with some success
        if stats["success_rate"] > 0:
            # Score is weighted by average attempts
            score = stats["avg_attempts"]
            if score < best_score:
                best_score = score
                best_combo = stats["params"]

    if best_combo:
        print("\nBest parameter combination:")
        for key, value in best_combo.items():
            print(f"  {key}: {value}")
        print(
            f"Average attempts (including failures as {max_attempts}): {best_score:.1f}"
        )
    else:
        print("No successful parameter combinations found")

    print(f"Complete results saved to {output_file}")
    print(f"Summary saved to {summary_file}")

    return summary


if __name__ == "__main__":
    # Generate a timestamp for the output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"grid_search_results_{timestamp}.json"

    # Run grid search with moderate settings to make it feasible
    grid_search_summary = grid_search_schedule_params(
        output_file=output_file, trials_per_combo=20, max_attempts=2000
    )
