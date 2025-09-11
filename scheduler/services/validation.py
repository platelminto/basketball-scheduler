"""
Schedule validation service functions.

This module contains business logic for validating schedules using
various test functions and orchestrating validation results.
"""

from tests import (
    pairing_tests,
    cycle_pairing_test,
    referee_player_test,
    adjacent_slot_test,
    one_ref_per_week_test,
)
from .stats import compute_schedule_statistics


def run_all_validation_tests(schedule_data, teams_per_level):
    """Run all validation tests and return aggregated results."""

    validation_results = {}

    # Run Pairing Test
    pt_passed, pt_errors = pairing_tests(schedule_data, teams_per_level)
    validation_results["Pairings"] = {
        "passed": pt_passed,
        "message": "Teams play the correct number of times based on their level size.",
        "errors": pt_errors,
    }

    # Run Cycle Pairing Test
    cpt_passed, cpt_errors = cycle_pairing_test(
        schedule_data, teams_per_level
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

    # Run One Ref Per Week Test
    orpw_passed, orpw_errors = one_ref_per_week_test(schedule_data)
    validation_results["One Ref Per Week"] = {
        "passed": orpw_passed,
        "message": "Teams can only referee once per week (game day).",
        "errors": orpw_errors,
    }

    return validation_results


def validate_schedule_data(data):
    """Validate schedule data and configuration, including statistics."""
    try:
        schedule_data = data["schedule"]
        teams_per_level = data["teams_per_level"]

        validation_results = run_all_validation_tests(schedule_data, teams_per_level)

        statistics = compute_schedule_statistics(schedule_data, teams_per_level)

        return {
            "validation": validation_results,
            "statistics": statistics
        }
    except KeyError as e:
        raise ValueError(f"Missing required data: {e}")
    except Exception as e:
        raise Exception(f"An internal error occurred during validation: {e}")