import random
from itertools import product, permutations
import math
import copy
from multiprocessing import Pool, cpu_count
import json
import os
import time
from utils import (
    load_schedule_from_file,
    convert_to_formatted_schedule,
    save_schedule_to_file,
    print_schedule,
)
import itertools
from datetime import datetime
from django.http import JsonResponse
from tests import (
    pairing_tests,
    cycle_pairing_test,
    referee_player_test,
    adjacent_slot_test,
    global_slot_distribution_test,
    mirror_pairing_test,
)
from stats import print_statistics

###########################
# Default Configuration (can be overridden during instantiation)
###########################
DEFAULT_CONFIG = {
    # League structure
    "levels": ["A", "B", "C"],  # Names of the levels/divisions
    "teams_per_level": {  # Number of teams in each level
        "A": 6,
        "B": 6,
        "C": 6,
    },
    "first_half_weeks": 5,
    "total_weeks": 10,
    "num_slots": 4,
    # Schedule structure
    "courts_per_slot": {
        1: [1, 1, 2, 2, 2, 2, 2, 2, 2, 2],
        2: [3, 3, 2, 2, 2, 2, 2, 2, 2, 2],
        3: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        4: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
    },  # Number of courts available in each slot
    # Constraints for play balance
    # These are the maximum number of games a team can play in a slot for the whole season.
    "slot_limits": {
        1: 4,  # Teams can play at most 3 games in slot 1
        2: 6,  # Teams can play at most 6 games in slots 2 and 3
        3: 6,
        4: 4,  # Teams can play at most 4 games in slot 4
    },
    # Constraints for referee balance
    "min_referee_count": 3,  # Minimum times a team must referee in a season per level
    "max_referee_count": 7,  # Maximum times a team can referee in a season per level
    # Optimization priorities
    "priority_slots": [1, 4],  # Slots where balance is more important
    "priority_multiplier": 100,  # Extra weight for priority slots in balance calculations
}

DEFAULT_CONFIG["team_names_by_level"] = {level: [f"{level}Team{i+1}" for i in range(DEFAULT_CONFIG["teams_per_level"][level])] for level in DEFAULT_CONFIG["levels"]}
    

# Top-level helper function for multiprocessing
def _run_find_schedule_attempt(config):
    """Helper function to run a single attempt in a separate process."""
    # Create a temporary Scheduler instance in the worker process
    temp_scheduler = Scheduler(config)
    # Call the instance method to perform one attempt
    return temp_scheduler.find_schedule_attempt()


class Scheduler:
    def __init__(self, config=None):
        """
        Initializes the Scheduler with a given configuration.

        Args:
            config (dict): The configuration dictionary for the schedule.
        """
        self.config = DEFAULT_CONFIG
        if config:
            self.config.update(config)
        self._validate_config()
        
        # Derive teams from config and store
        self.teams = {
            level: list(range(self.config["teams_per_level"][level]))
            for level in self.config["levels"]
        }
        self.raw_schedule = None  # To store the result before formatting

    ###########################
    # Parameters & Round-Robin
    ###########################

    def generate_round_robin_pairings(self, n):
        """
        Generate a round-robin schedule for n teams using the circle method.
        Returns a list of rounds (each round is a list of games, where a game is a tuple of two team indices).
        For n even there will be n-1 rounds.
        """
        # No changes needed in the logic itself
        teams_list = list(range(n))
        rounds = []
        for i in range(n - 1):
            round_games = []
            for j in range(n // 2):
                t1 = teams_list[j]
                t2 = teams_list[n - 1 - j]
                round_games.append(tuple(sorted((t1, t2))))
            rounds.append(round_games)
            teams_list = [teams_list[0]] + [teams_list[-1]] + teams_list[1:-1]
        return rounds

    #############################################
    # Candidate Slot Assignment (per level)
    #############################################

    def generate_level_slot_assignments(self, level, num_games):
        """
        Generate candidate slot assignments for a level's round (num_games games).
        Each candidate is a tuple of length num_games with values in {1,...,self.config["num_slots"]}.

        Local constraints:
        - For each slot s, the number of games assigned to s is <= teams//3.
        - There must be at least 2 distinct slots used.
        - The set of slots used must be contiguous (e.g. {2,3} is okay; {1,3} is not).
        """
        assignments = []
        # Use self.config
        num_slots = self.config["num_slots"]
        num_teams = self.config["teams_per_level"][level]
        max_local = (
            num_teams // 3
        )  # Each game needs 2 teams playing + 1 team refereeing

        for candidate in product(range(1, num_slots + 1), repeat=num_games):
            # Count all slots at once instead of using any() with multiple count() calls
            slot_counts = {}
            for s in candidate:
                slot_counts[s] = slot_counts.get(s, 0) + 1

            # Check if we have at least 2 distinct slots before sorting
            if len(slot_counts) < 2:
                continue

            # Check if any slot exceeds max_local without using any()
            exceeds_max = False
            for count in slot_counts.values():
                if count > max_local:
                    exceeds_max = True
                    break
            if exceeds_max:
                continue

            # Check contiguity - find min and max slot
            min_slot = min(slot_counts.keys())
            max_slot = max(slot_counts.keys())

            # For contiguous slots, every slot between min and max must be used
            if max_slot - min_slot + 1 == len(slot_counts):
                assignments.append(candidate)

        return assignments

    #############################################
    # Candidate Referee Assignment Functions
    #############################################

    def candidate_referees_for_game(self, level, slot_assignment, pairing, game_index):
        """
        For a given game (indexed by game_index) in a round,
        return the list of teams eligible to referee that game.
        A team is eligible if:
        - It is not playing in that game.
        - Its own playing game (from pairing) is scheduled in a slot differing by exactly 1.
        """
        team_to_game = {}
        for i, pair in enumerate(pairing):
            for t in pair:
                team_to_game[t] = i
        candidates = []
        slot = slot_assignment[game_index]
        # Use self.config
        for t in range(self.config["teams_per_level"][level]):
            if t in pairing[game_index]:
                continue
            # Check if team t has a game assigned in this round's pairing
            if t not in team_to_game:
                # This can happen if a team has a bye, skip eligibility check
                continue
            j = team_to_game[t]
            if abs(slot_assignment[j] - slot) == 1:
                candidates.append(t)
        return candidates

    def get_ref_assignment(self, level, slot_assignment, pairing, current_ref_counts):
        """
        Given a slot_assignment for a round (a tuple of slots for each game) and
        fixed pairings, return a tuple of referee assignments (one per game) that:
        - Each referee is eligible per self.candidate_referees_for_game.
        - The referees are distinct.
        If multiple valid assignments exist, choose one minimizing the sum of current referee counts.
        """
        # Get candidate lists first
        candidate_lists = []
        for i in range(len(pairing)):
            # Call self method
            candidates = self.candidate_referees_for_game(
                level, slot_assignment, pairing, i
            )
            # Early exit: if any game has no candidates, no valid assignment exists
            if not candidates:
                return None
            candidate_lists.append(candidates)

        # Try a greedy approach first - this might give a good enough solution quickly
        # Use self.config
        num_teams = self.config["teams_per_level"][level]
        used = [False] * num_teams
        greedy_assignment = []

        # Sort games by number of candidates
        games_order = sorted(
            range(len(candidate_lists)), key=lambda i: len(candidate_lists[i])
        )

        for game_idx in games_order:
            # Sort candidates by referee count (prefer refs who've done it less)
            candidates = sorted(
                candidate_lists[game_idx], key=lambda t: current_ref_counts.get(t, 0)
            )

            # Find first unused referee
            assigned = False
            for referee in candidates:
                # Check bounds for 'used' list
                if 0 <= referee < len(used) and not used[referee]:
                    greedy_assignment.append((game_idx, referee))
                    used[referee] = True
                    assigned = True
                    break

            if not assigned:
                # Greedy approach failed, fall back to original method
                break

        # If greedy approach succeeded, convert to proper format and return
        if len(greedy_assignment) == len(pairing):
            # Sort by game index to restore original order
            greedy_assignment.sort()
            return tuple(ref for _, ref in greedy_assignment)

        # Fall back to original method if greedy approach fails
        valid_assignments = []
        scores = []

        # Original approach for smaller search spaces
        try:
            # Check if candidate_lists is empty or contains empty lists before product
            if not candidate_lists or any(not sublist for sublist in candidate_lists):
                return None  # Cannot generate product

            for assignment in product(*candidate_lists):
                if len(set(assignment)) == len(
                    assignment
                ):  # Ensure referees are distinct
                    valid_assignments.append(assignment)
                    scores.append(sum(current_ref_counts.get(t, 0) for t in assignment))
        except OverflowError:
            print(
                f"Warning: OverflowError during referee assignment product calculation for level {level}. Skipping this candidate."
            )
            return None

        if not valid_assignments:
            return None
        # Handle case where min(scores) might not exist if scores is empty
        if not scores:
            return None  # Should be caught earlier, but safeguard
        min_score = min(scores)
        # Find the first occurrence of min_score
        min_index = -1
        for i, score in enumerate(scores):
            if score == min_score:
                min_index = i
                break
        if min_index != -1:
            return valid_assignments[min_index]
        else:
            return None  # Should not happen if valid_assignments is not empty

    #############################################
    # Backtracking Solver for Half Schedules (Direct Slot Assignment)
    #############################################

    # Removed 'teams' argument, uses self.teams and self.config instead
    def solve_half_schedule(self, rr_pairings, weeks, initial_ref_counts=None):
        """
        For each week, for each level assign a candidate slot assignment (and corresponding referee assignment)
        that meets both local and global constraints. Uses self.teams and self.config.

        Global constraints (per week):
        - The sum of games assigned to a slot (across levels) does not exceed the courts available in that slot.
        """
        if initial_ref_counts is None:
            ref_counts = {
                level: {t: 0 for t in self.teams[level]}
                for level in self.config["levels"]
            }
        else:
            ref_counts = {
                level: dict(initial_ref_counts[level])
                for level in self.config["levels"]
            }
        schedule = [None] * weeks

        def backtrack(week):
            if week == weeks:
                return True
            # Global usage per slot for this week.
            global_usage = {s: 0 for s in range(1, self.config["num_slots"] + 1)}
            week_assignment = {}
            # Copy referee counts to update as we assign each level.
            new_ref_counts = {
                level: dict(ref_counts[level]) for level in self.config["levels"]
            }

            def assign_level(i, current_usage):
                if i == len(self.config["levels"]):
                    return True
                level = self.config["levels"][i]
                pairing = rr_pairings[level][
                    week
                ]  # Fixed round-robin pairing for this level.
                num_games = len(pairing)
                # Call self method
                candidate_assignments = self.generate_level_slot_assignments(
                    level, num_games
                )
                random.shuffle(candidate_assignments)
                for slot_assignment in candidate_assignments:
                    # Count how many games in each slot for this candidate.
                    candidate_count = {
                        s: slot_assignment.count(s)
                        for s in range(1, self.config["num_slots"] + 1)
                    }
                    # Check global capacity: for each slot, usage + candidate_count <= courts available for this week.
                    feasible = True
                    for s in range(1, self.config["num_slots"] + 1):
                        # Check if slot s exists for the current week in the config
                        if s in self.config["courts_per_slot"] and week < len(
                            self.config["courts_per_slot"][s]
                        ):
                            if (
                                current_usage[s] + candidate_count.get(s, 0)
                                > self.config["courts_per_slot"][s][week]
                            ):
                                feasible = False
                                break
                        elif (
                            candidate_count.get(s, 0) > 0
                        ):  # Trying to assign to a non-existent/undefined slot
                            feasible = False
                            break

                    if not feasible:
                        continue
                    # Try to get a referee assignment for this candidate. Call self method
                    ref_assignment = self.get_ref_assignment(
                        level, slot_assignment, pairing, new_ref_counts[level]
                    )
                    if ref_assignment is None:
                        continue
                    # Update current usage.
                    for s in range(1, self.config["num_slots"] + 1):
                        current_usage[s] += candidate_count.get(s, 0)
                    week_assignment[level] = (slot_assignment, pairing, ref_assignment)
                    for t in ref_assignment:
                        # Ensure team t exists in the counts before incrementing
                        if t in new_ref_counts[level]:
                            new_ref_counts[level][t] += 1
                        else:
                            # This might indicate an issue if a referee is assigned who isn't in self.teams[level]
                            print(
                                f"Warning: Referee {t} not found in level {level} teams during backtrack."
                            )
                            # Decide how to handle: skip? initialize? For now, let's initialize.
                            new_ref_counts[level][t] = 1

                    # Recurse to the next level.
                    if assign_level(i + 1, current_usage):
                        return True
                    # Backtrack.
                    for s in range(1, self.config["num_slots"] + 1):
                        current_usage[s] -= candidate_count.get(s, 0)
                    # Ensure ref_assignment is valid before decrementing counts
                    valid_ref_assignment = [
                        t for t in ref_assignment if t in new_ref_counts[level]
                    ]
                    if len(valid_ref_assignment) != len(ref_assignment):
                        print(
                            f"Warning: Mismatch in referee assignment during backtrack for level {level}, week {week}."
                        )

                    for t in valid_ref_assignment:
                        # Check if count is positive before decrementing
                        if new_ref_counts[level][t] > 0:
                            new_ref_counts[level][t] -= 1
                        else:
                            # This indicates a potential logic error or issue with state tracking
                            print(
                                f"Warning: Attempted to decrement non-positive ref count for team {t} in level {level}."
                            )

                    # Delete the assignment for the current level before returning False
                    if level in week_assignment:
                        del week_assignment[level]

                return False

            if not assign_level(0, global_usage):
                return False
            schedule[week] = week_assignment
            for level in self.config["levels"]:
                ref_counts[level] = new_ref_counts[level]
            return backtrack(week + 1)

        if backtrack(0):
            return schedule, ref_counts
        else:
            return None, None

    # Removed 'teams' argument, uses self.teams and self.config instead
    def solve_second_half(self, rr_pairings, first_half_schedule, initial_ref_counts):
        """
        Solve the second half of the schedule using self.teams and self.config.

        For each level and week (in the second half), we use the pairing from the
        corresponding week in the first half (to preserve the mirror property).
        We then assign slots (and corresponding referee assignments) using the same
        direct game-by-game backtracking approach with global usage constraints.
        """
        weeks = self.config["first_half_weeks"]
        ref_counts = {
            level: dict(initial_ref_counts[level]) for level in self.config["levels"]
        }
        schedule = [None] * weeks  # Schedule for the second half

        def backtrack(week):  # week is 0-based index within the second half
            if week == weeks:
                return True
            global_usage = {s: 0 for s in range(1, self.config["num_slots"] + 1)}
            week_assignment = {}
            new_ref_counts = {
                level: dict(ref_counts[level]) for level in self.config["levels"]
            }

            def assign_level(i, current_usage):
                if i == len(self.config["levels"]):
                    return True
                level = self.config["levels"][i]
                # Use the pairing from the first half schedule for this level and corresponding week.
                # Ensure first_half_schedule[week] and subsequent indices are valid
                if (
                    week >= len(first_half_schedule)
                    or level not in first_half_schedule[week]
                    or len(first_half_schedule[week][level]) < 2
                ):
                    print(
                        f"Error: Invalid structure in first_half_schedule at week {week}, level {level}"
                    )
                    return False  # Cannot proceed if structure is wrong
                pairing = first_half_schedule[week][level][1]

                num_games = len(pairing)
                # Call self method
                candidate_assignments = self.generate_level_slot_assignments(
                    level, num_games
                )
                random.shuffle(candidate_assignments)

                for slot_assignment in candidate_assignments:
                    # Count how many games in each slot this candidate assignment would add.
                    candidate_count = {
                        s: slot_assignment.count(s)
                        for s in range(1, self.config["num_slots"] + 1)
                    }
                    # Check that global capacity is not exceeded for this specific week in the second half.
                    # Calculate the actual week index in the full schedule
                    full_schedule_week_index = week + weeks
                    feasible = True
                    for s in range(1, self.config["num_slots"] + 1):
                        # Check if slot s exists for the current week in the config
                        if s in self.config[
                            "courts_per_slot"
                        ] and full_schedule_week_index < len(
                            self.config["courts_per_slot"][s]
                        ):
                            if (
                                current_usage[s] + candidate_count.get(s, 0)
                                > self.config["courts_per_slot"][s][
                                    full_schedule_week_index
                                ]
                            ):
                                feasible = False
                                break
                        elif (
                            candidate_count.get(s, 0) > 0
                        ):  # Trying to assign to non-existent/undefined slot
                            feasible = False
                            break

                    if not feasible:
                        continue
                    # Try to assign referees given this candidate slot assignment. Call self method
                    ref_assignment = self.get_ref_assignment(
                        level, slot_assignment, pairing, new_ref_counts[level]
                    )
                    if ref_assignment is None:
                        continue
                    # If successful, update current usage and referee counts.
                    for s in range(1, self.config["num_slots"] + 1):
                        current_usage[s] += candidate_count.get(s, 0)
                    week_assignment[level] = (slot_assignment, pairing, ref_assignment)

                    for t in ref_assignment:
                        if t in new_ref_counts[level]:
                            new_ref_counts[level][t] += 1
                        else:
                            print(
                                f"Warning: Referee {t} not found in level {level} teams during second half backtrack."
                            )
                            new_ref_counts[level][t] = 1  # Initialize if not found

                    # Proceed to the next level.
                    if assign_level(i + 1, current_usage):
                        return True
                    # Backtrack.
                    for s in range(1, self.config["num_slots"] + 1):
                        current_usage[s] -= candidate_count.get(s, 0)

                    # Ensure ref_assignment is valid before decrementing counts
                    valid_ref_assignment = [
                        t for t in ref_assignment if t in new_ref_counts[level]
                    ]
                    if len(valid_ref_assignment) != len(ref_assignment):
                        print(
                            f"Warning: Mismatch in referee assignment during second half backtrack for level {level}, week {week}."
                        )

                    for t in valid_ref_assignment:
                        if new_ref_counts[level][t] > 0:
                            new_ref_counts[level][t] -= 1
                        else:
                            print(
                                f"Warning: Attempted to decrement non-positive ref count for team {t} in level {level} (second half)."
                            )

                    # Delete the assignment for the current level before returning False
                    if level in week_assignment:
                        del week_assignment[level]

                return False

            if not assign_level(0, global_usage):
                return False
            # Store the assignment for the current week (relative to second half)
            schedule[week] = week_assignment
            for level in self.config["levels"]:
                ref_counts[level] = new_ref_counts[level]
            return backtrack(week + 1)

        if backtrack(0):
            return schedule, ref_counts
        else:
            return None, None

    ##############################################
    # Phase 1: Balance Team Play Counts (Post-Processing)
    ##############################################

    # Removed 'teams' argument, uses self.teams and self.config instead
    def weighted_play_imbalance_metric(self, schedule):
        """
        Compute a weighted global imbalance metric based on configured limits using self.teams and self.config.
        For each level and team for each slot, if the actual count exceeds the limit,
        add: violation_penalty * (count - limit)^2.
        For priority slots, multiply the penalty by an extra multiplier.
        Lower values indicate better balance.
        """
        # Call self method
        play_counts = self.compute_team_play_counts(
            schedule
        )  # level -> {team -> {slot: count}}
        total = 0.0
        violation_penalty = 1e6  # Penalty factor for exceeding the limit

        for level in self.config["levels"]:
            for t in self.teams[level]:
                for s in range(1, self.config["num_slots"] + 1):
                    count = play_counts[level][t][s]
                    # Get limit from self.config
                    limit = self.config["slot_limits"].get(s, float("inf"))

                    if count > limit:
                        # Apply extra multiplier for priority slots
                        if s in self.config["priority_slots"]:
                            total += (
                                violation_penalty
                                * self.config["priority_multiplier"]
                                * (count - limit) ** 2
                            )
                        else:
                            total += violation_penalty * (count - limit) ** 2
        return total

    # Removed 'teams' argument, uses self.teams and self.config instead
    def compute_team_play_counts(self, schedule):
        """
        For each level, compute a dict: team -> {slot: count} of playing appearances using self.teams and self.config.
        Each game in a week (for a level) contributes 1 appearance in its slot for each team playing.
        """
        counts = {
            level: {
                t: {s: 0 for s in range(1, self.config["num_slots"] + 1)}
                for t in self.teams[level]
            }
            for level in self.config["levels"]
        }
        if schedule is None:
            return counts  # Handle empty schedule case

        for week_data in schedule:
            if week_data is None:
                continue  # Skip potentially None weeks during generation
            for level in self.config["levels"]:
                if level not in week_data:
                    continue  # Skip if level data is missing for this week
                # Ensure the structure is as expected
                if len(week_data[level]) < 3:
                    print(
                        f"Warning: Unexpected structure in schedule data for level {level}. Skipping week."
                    )
                    continue
                distribution, pairing, _ = week_data[level]
                # Add checks for distribution and pairing lengths/types if necessary
                if len(distribution) != len(pairing):
                    print(
                        f"Warning: Mismatch between distribution and pairing length for level {level}. Skipping."
                    )
                    continue

                for i in range(len(pairing)):
                    slot = distribution[i]
                    # Ensure slot is valid before accessing counts
                    if slot not in range(1, self.config["num_slots"] + 1):
                        print(
                            f"Warning: Invalid slot number {slot} encountered for level {level}. Skipping game."
                        )
                        continue
                    # Ensure pairing structure is valid
                    if len(pairing[i]) != 2:
                        print(
                            f"Warning: Invalid pairing {pairing[i]} encountered for level {level}. Skipping game."
                        )
                        continue
                    t1, t2 = pairing[i]

                    # Ensure teams are valid for the level before incrementing
                    if t1 in counts[level] and t2 in counts[level]:
                        counts[level][t1][slot] += 1
                        counts[level][t2][slot] += 1
                    else:
                        print(
                            f"Warning: Invalid team(s) {t1}, {t2} encountered in pairing for level {level}. Skipping count update."
                        )
        return counts

    ##############################################
    # Phase 2: Referee Post-Processing
    ##############################################

    # Removed 'teams' argument, uses self.teams and self.config instead
    def compute_overall_ref_counts(self, schedule):
        """Computes overall referee counts using self.teams and self.config."""
        counts = {
            level: {t: 0 for t in self.teams[level]} for level in self.config["levels"]
        }
        if schedule is None:
            return counts  # Handle empty schedule

        for week_data in schedule:
            if week_data is None:
                continue  # Skip potentially None weeks
            for level in self.config["levels"]:
                if level not in week_data:
                    continue  # Skip if level data is missing
                # Ensure expected structure
                if len(week_data[level]) < 3:
                    print(
                        f"Warning: Unexpected structure in schedule data for level {level} (ref counts). Skipping week."
                    )
                    continue
                _, _, ref_assignment = week_data[level]
                # Ensure ref_assignment is iterable
                if not isinstance(ref_assignment, (list, tuple)):
                    print(
                        f"Warning: Invalid ref_assignment type {type(ref_assignment)} for level {level}. Skipping."
                    )
                    continue

                for r in ref_assignment:
                    # Ensure referee team is valid for the level
                    if r in counts[level]:
                        counts[level][r] += 1
                    else:
                        print(
                            f"Warning: Invalid referee {r} encountered for level {level}. Skipping count update."
                        )
        return counts

    def total_ref_imbalance(self, level, ref_counts):
        """Compute the variance of referee counts for a given level using self.config."""
        team_list = list(range(self.config["teams_per_level"][level]))
        values = [ref_counts.get(t, 0) for t in team_list]
        # Avoid division by zero if team_list is empty (shouldn't happen with validation)
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values)

    def is_week_global_valid(self, week_assignment, week_index):
        """
        Check that for the given week assignment, the total number of games assigned
        to each slot exactly equals the expected value from self.config["courts_per_slot"]
        for the specific week.
        """
        usage = {s: 0 for s in range(1, self.config["num_slots"] + 1)}
        if week_assignment is None:
            return False  # Invalid if week data is None

        for level in week_assignment:
            # Ensure expected structure
            if level not in week_assignment or len(week_assignment[level]) < 1:
                print(
                    f"Warning: Invalid structure for level {level} in week_assignment (is_week_global_valid)."
                )
                return False  # Cannot validate if structure is wrong
            slot_assignment, _, _ = week_assignment[level]
            # Ensure slot_assignment is iterable
            if not isinstance(slot_assignment, (list, tuple)):
                print(
                    f"Warning: Invalid slot_assignment type {type(slot_assignment)} for level {level}."
                )
                return False  # Cannot validate

            for s in slot_assignment:
                # Check if slot 's' is valid before using it as a key in usage
                if s in usage:
                    usage[s] += 1
                else:
                    print(
                        f"Warning: Encountered invalid slot number {s} in level {level} assignment."
                    )
                    return False  # Invalid slot means week is invalid

        for s in usage:
            expected_courts = 0
            # Check if slot 's' and week_index are valid for the config
            if s in self.config["courts_per_slot"] and week_index < len(
                self.config["courts_per_slot"][s]
            ):
                expected_courts = self.config["courts_per_slot"][s][week_index]
            else:
                # If the config doesn't define courts for this slot/week, but usage is > 0, it's invalid.
                if usage[s] > 0:
                    print(
                        f"Warning: Games assigned to slot {s} in week {week_index}, but not defined in config."
                    )
                    return False

            if usage[s] != expected_courts:
                # print(f"Debug: Week {week_index}, Slot {s}: Usage {usage[s]} != Expected {expected_courts}") # Optional debug
                return False
        return True

    # Removed 'teams' argument, uses self.teams and self.config instead
    def composite_objective(self, schedule, weight_play=1.0, weight_ref=1.0):
        """
        Compute the composite objective from play imbalance and referee imbalance only, using self.teams and self.config.
        (Global slot distribution is now enforced as a hard constraint.)
        """
        # Call self methods
        play_cost = self.weighted_play_imbalance_metric(schedule)
        overall_ref_counts = self.compute_overall_ref_counts(schedule)
        ref_cost = 0
        for level in self.config["levels"]:
            # Ensure level exists in overall ref counts
            if level in overall_ref_counts:
                # Call self method
                ref_cost += self.total_ref_imbalance(level, overall_ref_counts[level])
            else:
                # Handle case where level might be missing (e.g., empty schedule)
                print(
                    f"Warning: Level {level} not found in overall ref counts for composite objective."
                )
                # Decide how to handle: add 0 cost? Add penalty? Assume 0 for now.
                pass
        return weight_play * play_cost + weight_ref * ref_cost

    # Removed 'teams' argument, uses self.teams and self.config instead
    # Update balance_schedule to accept the new parameters
    def balance_schedule(
        self,
        schedule,
        max_iterations=200,
        weight_play=0.1,
        weight_ref=10.0,
        cooling_rate=0.9,
        initial_temp=5.0,
        candidate_prob=1.0,
        swap_prob=0.0,
    ):
        """
        Merged local search that improves play and referee balance while enforcing a hard
        global slot distribution constraint. Any move that causes a week's slot usage to deviate
        from self.config["courts_per_slot"] is rejected. Uses self.teams and self.config.
        """
        # Check for None schedule input
        if schedule is None:
            print("Warning: balance_schedule received None schedule. Returning None.")
            return None

        # Normalize probabilities
        total_prob = candidate_prob + swap_prob
        # Avoid division by zero if both probs are 0
        if total_prob > 0:
            candidate_prob /= total_prob
            swap_prob /= total_prob
        else:  # Default if both are 0 (should not happen with defaults)
            candidate_prob = 1.0
            swap_prob = 0.0

        # Create initial copy - we still need one to avoid modifying the input
        new_schedule = copy.deepcopy(schedule)
        # Call self method
        current_obj = self.composite_objective(new_schedule, weight_play, weight_ref)

        # Track statistics to guide the search
        rejected_count = 0  # Currently unused, but kept for potential future analysis
        accepted_count = 0  # Currently unused

        # Identify imbalanced teams/slots for targeted improvement (Optional: currently not used in move selection)
        # play_counts = self.compute_team_play_counts(new_schedule)
        # ref_counts = self.compute_overall_ref_counts(new_schedule)
        # problematic_teams = {}
        # for level in self.config["levels"]:
        #     problematic_teams[level] = []
        #     for team in self.teams[level]:
        #         for slot, limit in self.config["slot_limits"].items():
        #             if play_counts[level][team][slot] > limit:
        #                 problematic_teams[level].append((team, slot))

        temperature = initial_temp

        for iteration in range(max_iterations):
            # Choose move type based on probabilities
            if random.random() < candidate_prob:
                move_type = "candidate"
            else:
                move_type = "swap"

            if move_type == "swap":
                # Ensure there are enough weeks to sample from
                if self.config["first_half_weeks"] < 2:
                    continue  # Cannot perform swap with less than 2 weeks

                # Swap move: choose two different weeks and one level; swap their assignments (and mirror weeks)
                try:
                    w1, w2 = random.sample(range(self.config["first_half_weeks"]), 2)
                except ValueError:  # Handle case if range is too small (e.g., 0 or 1)
                    continue
                level = random.choice(self.config["levels"])

                # Check if schedule structure is valid before accessing
                if (
                    w1 >= len(new_schedule)
                    or w2 >= len(new_schedule)
                    or new_schedule[w1] is None
                    or new_schedule[w2] is None
                    or level not in new_schedule[w1]
                    or level not in new_schedule[w2]
                ):
                    print(
                        f"Warning: Invalid schedule structure detected during swap attempt (w1={w1}, w2={w2}, level={level}). Skipping iteration."
                    )
                    continue

                # Save original assignments before swapping
                orig_w1 = new_schedule[w1][level]
                orig_w2 = new_schedule[w2][level]

                # Swap in-place
                new_schedule[w1][level] = orig_w2
                new_schedule[w2][level] = orig_w1

                # Handle mirror weeks
                mirror_w1 = w1 + self.config["first_half_weeks"]
                mirror_w2 = w2 + self.config["first_half_weeks"]
                orig_m1 = None
                orig_m2 = None

                # Check bounds and structure for mirror weeks before accessing
                valid_mirror_swap = True
                if mirror_w1 < len(new_schedule) and mirror_w2 < len(new_schedule):
                    if (
                        new_schedule[mirror_w1] is None
                        or new_schedule[mirror_w2] is None
                        or level not in new_schedule[mirror_w1]
                        or level not in new_schedule[mirror_w2]
                    ):
                        print(
                            f"Warning: Invalid schedule structure detected for mirror weeks during swap (mw1={mirror_w1}, mw2={mirror_w2}, level={level})."
                        )
                        valid_mirror_swap = (
                            False  # Cannot perform mirror swap if structure is bad
                        )
                    else:
                        orig_m1 = new_schedule[mirror_w1][level]
                        orig_m2 = new_schedule[mirror_w2][level]
                        new_schedule[mirror_w1][level] = orig_m2
                        new_schedule[mirror_w2][level] = orig_m1
                elif mirror_w1 < len(new_schedule) or mirror_w2 < len(new_schedule):
                    # If only one mirror week exists within bounds, swap is problematic/undefined for mirror part
                    print(
                        f"Warning: Asymmetric mirror weeks ({mirror_w1}, {mirror_w2}) relative to schedule length ({len(new_schedule)}). Mirror swap skipped."
                    )
                    valid_mirror_swap = False

                # Check constraints (call self method)
                is_valid = self.is_week_global_valid(
                    new_schedule[w1], w1
                ) and self.is_week_global_valid(new_schedule[w2], w2)
                # Only check mirror weeks if the swap was performed and they exist
                if valid_mirror_swap:
                    if mirror_w1 < len(new_schedule):
                        is_valid = is_valid and self.is_week_global_valid(
                            new_schedule[mirror_w1], mirror_w1
                        )
                    if mirror_w2 < len(new_schedule):
                        is_valid = is_valid and self.is_week_global_valid(
                            new_schedule[mirror_w2], mirror_w2
                        )

                accepted_move = False
                # Evaluate if the constraint is satisfied
                if is_valid:
                    # Call self method
                    candidate_obj = self.composite_objective(
                        new_schedule, weight_play, weight_ref
                    )
                    delta = candidate_obj - current_obj

                    # Always accept improvements or based on temperature
                    if delta < 0 or random.random() < math.exp(-delta / temperature):
                        current_obj = candidate_obj
                        accepted_move = True
                        # accepted_count += 1 # Currently unused

                # Revert changes if invalid or not accepted
                if not accepted_move:
                    # Ensure structure was valid before attempting revert
                    if (
                        w1 < len(schedule)
                        and w2 < len(schedule)
                        and schedule[w1] is not None
                        and schedule[w2] is not None
                        and level in schedule[w1]
                        and level in schedule[w2]
                    ):
                        new_schedule[w1][level] = orig_w1
                        new_schedule[w2][level] = orig_w2
                    # Revert mirror only if original mirror assignments were saved
                    if (
                        orig_m1 is not None
                        and orig_m2 is not None
                        and mirror_w1 < len(schedule)
                        and mirror_w2 < len(schedule)
                        and schedule[mirror_w1] is not None
                        and schedule[mirror_w2] is not None
                        and level in schedule[mirror_w1]
                        and level in schedule[mirror_w2]
                    ):
                        new_schedule[mirror_w1][level] = orig_m1
                        new_schedule[mirror_w2][level] = orig_m2

            else:  # candidate move
                # Try a new slot assignment for a random week and level
                if self.config["first_half_weeks"] == 0:
                    continue  # Cannot choose week if none exist

                w = random.randrange(self.config["first_half_weeks"])
                level = random.choice(self.config["levels"])

                # Check schedule structure before proceeding
                if (
                    w >= len(new_schedule)
                    or new_schedule[w] is None
                    or level not in new_schedule[w]
                    or len(new_schedule[w][level]) < 3
                ):
                    print(
                        f"Warning: Invalid schedule structure detected during candidate move attempt (w={w}, level={level}). Skipping."
                    )
                    continue

                current_assignment, pairing, current_ref = new_schedule[w][level]

                # Generate alternative assignments (call self method)
                candidates = self.generate_level_slot_assignments(level, len(pairing))
                # Ensure current_assignment is a tuple for comparison if needed
                current_assignment_tuple = (
                    tuple(current_assignment)
                    if isinstance(current_assignment, list)
                    else current_assignment
                )
                # Filter out the current assignment
                candidates = [a for a in candidates if a != current_assignment_tuple]

                if not candidates:
                    continue

                new_assignment = random.choice(candidates)
                # Try to get a referee assignment, initializing counts to 0 for this attempt (call self method)
                # Use self.teams to get the list of teams for the level
                new_ref = self.get_ref_assignment(
                    level, new_assignment, pairing, {t: 0 for t in self.teams[level]}
                )
                if new_ref is None:
                    continue

                # Save original state and make change
                original_week_assignment = new_schedule[w][level]
                new_schedule[w][level] = (new_assignment, pairing, new_ref)

                # Handle mirror week
                mirror_w = w + self.config["first_half_weeks"]
                original_mirror_assignment = None
                valid_mirror_update = True

                if mirror_w < len(new_schedule):
                    # Check mirror week structure
                    if (
                        new_schedule[mirror_w] is None
                        or level not in new_schedule[mirror_w]
                        or len(new_schedule[mirror_w][level]) < 3
                    ):
                        print(
                            f"Warning: Invalid structure for mirror week {mirror_w}, level {level} during candidate move. Skipping mirror update."
                        )
                        valid_mirror_update = False
                    else:
                        mirror_assignment, mirror_pairing, current_mirror_ref = (
                            new_schedule[mirror_w][level]
                        )
                        # Generate a *new* ref assignment for the mirror week based on its existing slot assignment
                        # This assumes the mirror week's slot assignment doesn't change in this move type.
                        # Use self.teams for the list of teams.
                        mirror_ref = self.get_ref_assignment(
                            level,
                            mirror_assignment,  # Use existing mirror slot assignment
                            mirror_pairing,
                            {
                                t: 0 for t in self.teams[level]
                            },  # Base counts for this attempt
                        )
                        if mirror_ref is None:
                            # If we can't find refs for the mirror week with its current slots, this candidate move is problematic
                            print(
                                f"Warning: Could not find valid ref assignment for mirror week {mirror_w}, level {level}. Reverting candidate move."
                            )
                            # Revert the main week change immediately and skip rest of iteration
                            new_schedule[w][level] = original_week_assignment
                            continue  # Skip to next iteration

                        original_mirror_assignment = new_schedule[mirror_w][
                            level
                        ]  # Save state
                        # Update only the referee part of the mirror week
                        new_schedule[mirror_w][level] = (
                            mirror_assignment,
                            mirror_pairing,
                            mirror_ref,
                        )

                # Check global constraints (call self method)
                is_valid = self.is_week_global_valid(new_schedule[w], w)
                if (
                    mirror_w < len(new_schedule) and valid_mirror_update
                ):  # Only check mirror if it exists and was updated
                    is_valid = is_valid and self.is_week_global_valid(
                        new_schedule[mirror_w], mirror_w
                    )

                accepted_move = False
                if is_valid:
                    # Call self method
                    candidate_obj = self.composite_objective(
                        new_schedule, weight_play, weight_ref
                    )
                    delta = candidate_obj - current_obj

                    # Always accept improvements or based on temperature
                    if delta < 0 or random.random() < math.exp(-delta / temperature):
                        current_obj = candidate_obj
                        accepted_move = True
                        # accepted_count += 1 # Currently unused

                # Revert changes if invalid or not accepted
                if not accepted_move:
                    # Revert main week change
                    new_schedule[w][level] = original_week_assignment
                    # Revert mirror week change only if it was modified
                    if original_mirror_assignment is not None and mirror_w < len(
                        new_schedule
                    ):
                        new_schedule[mirror_w][level] = original_mirror_assignment

            # Cool the temperature
            temperature *= cooling_rate
            # Avoid temperature becoming too close to zero
            if temperature < 1e-6:
                temperature = 1e-6

        # print(f"Balancing finished. Final objective: {current_obj}") # Optional debug
        return new_schedule

    #########################################
    # Run Post-Processing Phases & Testing
    #########################################

    # Removed 'teams' and 'levels' arguments, uses self.teams and self.config instead
    def validate_schedule(self, schedule):
        """
        Validate schedule against configured limits using self.teams and self.config:
        1. Teams must referee between min_referee_count and max_referee_count times in any level
        2. Teams must play within the configured slot limits
        Returns (bool, str) - (is_valid, error_message)
        """
        if schedule is None:
            return False, "Schedule is None"

        # Check referee counts (call self method)
        ref_counts = self.compute_overall_ref_counts(schedule)

        min_ref = self.config["min_referee_count"]
        max_ref = self.config["max_referee_count"]

        for level in self.config["levels"]:
            for team in self.teams[level]:
                count = ref_counts.get(level, {}).get(team, 0)
                if count > max_ref or count < min_ref:
                    return (
                        False,
                        f"Team {team+1} referees {count} times in level {level} "
                        f"(should be between {min_ref} and {max_ref})",
                    )

        # Check slot limits (call self method)
        play_counts = self.compute_team_play_counts(schedule)

        for level in self.config["levels"]:
            for team in self.teams[level]:
                for slot, limit in self.config["slot_limits"].items():
                    # Ensure level, team, and slot exist before accessing count
                    count = play_counts.get(level, {}).get(team, {}).get(slot, 0)
                    if count > limit:
                        return (
                            False,
                            f"Team {team+1} plays {count} times in slot {slot} "
                            f"in level {level} (max is {limit})",
                        )

        # Add check for global slot validity per week
        for week_index, week_assignment in enumerate(schedule):
            if not self.is_week_global_valid(week_assignment, week_index):
                return (
                    False,
                    f"Week {week_index+1} fails global slot distribution check.",
                )

        return True, "Schedule is valid"

    # Removed 'teams' argument, uses self.teams and self.config instead
    def find_schedule_attempt(self):
        """Single attempt to find a valid schedule using instance config and teams"""
        # Generate fixed round-robin pairings for each level.
        rr_pairings = {}
        for level in self.config["levels"]:
            # Call self method
            rr_pairings[level] = self.generate_round_robin_pairings(
                self.config["teams_per_level"][level]
            )

        # Solve first half - uses self.teams implicitly
        first_half_schedule, first_half_ref_counts = self.solve_half_schedule(
            rr_pairings, self.config["first_half_weeks"]  # Removed teams arg
        )
        if first_half_schedule is None:
            # print("Debug: Failed to solve first half.") # Optional
            return None

        # Solve second half - uses self.teams implicitly
        second_half_schedule, second_half_ref_counts = self.solve_second_half(
            rr_pairings, first_half_schedule, first_half_ref_counts  # Removed teams arg
        )
        if second_half_schedule is None:
            # print("Debug: Failed to solve second half.") # Optional
            return None

        # Ensure both halves have the expected number of weeks before concatenating
        if (
            len(first_half_schedule) != self.config["first_half_weeks"]
            or len(second_half_schedule) != self.config["first_half_weeks"]
        ):
            print(
                f"Warning: Mismatch in expected half lengths during concatenation. "
                f"First: {len(first_half_schedule)}/{self.config['first_half_weeks']}, "
                f"Second: {len(second_half_schedule)}/{self.config['first_half_weeks']}"
            )
            # Decide how to handle: return None? Try to proceed? Return None is safer.
            return None

        full_schedule = first_half_schedule + second_half_schedule

        # Balance schedule - uses self.teams implicitly
        # Pass balancing parameters from config if needed, or use defaults
        final_schedule = self.balance_schedule(full_schedule)  # Removed teams arg

        # Validate the schedule - uses self.teams implicitly
        is_valid, message = self.validate_schedule(
            final_schedule
        )  # Removed teams and levels args
        # Optional: print message only on failure? or control via verbosity setting?
        # print(f"Attempt validation result: {message}")
        if is_valid:
            return final_schedule
        # else:
        # print(f"Debug: Invalid schedule after balancing: {message}") # Optional
        return None

    # Renamed from validate_config, made private, uses self.config
    def _validate_config(self):
        """
        Validate the configuration parameters upon initialization.
        Raises ValueError with detailed message if any constraint is violated.
        """
        # Calculate total teams and games per level
        if not self.config.get("teams_per_level"):
            raise ValueError("Config missing 'teams_per_level'")
        total_teams = sum(self.config["teams_per_level"].values())
        # Ensure total_teams is even for pairing
        if total_teams % 2 != 0:
            raise ValueError(f"Sum of teams per level ({total_teams}) must be even.")
        total_games_per_round = total_teams // 2

        # 1. Check that sum of courts per slot equals total games per round for each week
        num_slots = self.config.get("num_slots", 0)
        if not self.config.get("courts_per_slot") or not isinstance(
            self.config["courts_per_slot"], dict
        ):
            raise ValueError("Config missing or invalid 'courts_per_slot'")
        # Determine number of weeks from the config (use slot 1 if available)
        if (
            1 not in self.config["courts_per_slot"]
            or not self.config["courts_per_slot"][1]
        ):
            raise ValueError(
                "Config 'courts_per_slot' must have data for slot 1 for all weeks."
            )
        num_weeks_from_courts = len(self.config["courts_per_slot"][1])
        # Check against total_weeks config
        if num_weeks_from_courts != self.config.get("total_weeks"):
            raise ValueError(
                f"Length of 'courts_per_slot' lists ({num_weeks_from_courts}) must match 'total_weeks' ({self.config.get('total_weeks')})"
            )

        for week_idx in range(num_weeks_from_courts):
            courts_sum = 0
            for s in range(1, num_slots + 1):
                # Check if slot exists and week_idx is valid
                if s in self.config["courts_per_slot"] and week_idx < len(
                    self.config["courts_per_slot"][s]
                ):
                    courts_sum += self.config["courts_per_slot"][s][week_idx]
                # else: implicitly adds 0, which is correct if the slot isn't used/defined for that week

            if courts_sum != total_games_per_round:
                raise ValueError(
                    f"Week {week_idx+1}: Sum of courts per slot ({courts_sum}) must equal total games per round "
                    f"({total_games_per_round})"
                )

        # 2. Check that entries in courts_per_slot match num_slots (optional, allows defining only used slots)
        # Let's relax this: only check that defined slots are within 1..num_slots
        for s in self.config["courts_per_slot"]:
            if not (1 <= s <= num_slots):
                raise ValueError(
                    f"Key {s} in courts_per_slot is outside the valid range 1-{num_slots}"
                )

        # 3. Check that each *defined* slot has values for all weeks
        for slot, weeks_data in self.config["courts_per_slot"].items():
            if len(weeks_data) != num_weeks_from_courts:
                raise ValueError(
                    f"Slot {slot} in courts_per_slot has {len(weeks_data)} weeks of data, "
                    f"but should have {num_weeks_from_courts}"
                )

        # 4. Check slot limits totals (optional sanity check)
        if (
            self.config.get("total_weeks", 0) > 0 and total_teams > 0
        ):  # Avoid division by zero
            # Games per team calculation might be slightly off for uneven divisions, but gives estimate
            # For round robin, it's total_weeks * (teams_in_level - 1) / teams_in_level * games_per_week ? No simpler...
            # Let's use a simpler check based on total games played
            total_games_in_season = total_games_per_round * self.config["total_weeks"]
            avg_games_per_team = (
                (total_games_in_season * 2) / total_teams if total_teams else 0
            )

            if self.config.get("slot_limits"):
                slot_limits_sum = sum(self.config["slot_limits"].values())
                # Relax the threshold check slightly, maybe just ensure sum > avg_games
                min_required = math.ceil(avg_games_per_team)
                if slot_limits_sum < min_required:
                    print(  # Make this a warning instead of error
                        f"Warning: Sum of slot limits ({slot_limits_sum}) is less than the average games "
                        f"per team ({avg_games_per_team:.2f}). This might make finding a valid schedule difficult."
                    )
            else:
                raise ValueError("Config missing 'slot_limits'")

        # 5. Check that priority slots count is reasonable (optional check)
        if self.config.get("priority_slots"):
            if len(self.config["priority_slots"]) > num_slots:
                print(  # Warning
                    f"Warning: Number of priority slots ({len(self.config['priority_slots'])}) "
                    f"exceeds total number of slots ({num_slots})."
                )
        # else: priority_slots is optional

        # 6. Ensure total_weeks is exactly double first_half_weeks
        if not self.config.get("first_half_weeks"):
            raise ValueError("Config missing 'first_half_weeks'")
        if self.config["total_weeks"] != self.config["first_half_weeks"] * 2:
            raise ValueError(
                f"Total weeks ({self.config['total_weeks']}) should be exactly double the first half weeks "
                f"({self.config['first_half_weeks']})"
            )

        # 7. Additional check: all priority slots should exist in the configuration
        if self.config.get("priority_slots"):
            for slot in self.config["priority_slots"]:
                if not (1 <= slot <= num_slots):
                    raise ValueError(
                        f"Priority slot {slot} is outside the valid range (1-{num_slots})"
                    )

        # 8. Check referee count limits
        if not isinstance(self.config.get("min_referee_count"), int) or not isinstance(
            self.config.get("max_referee_count"), int
        ):
            raise ValueError("min_referee_count and max_referee_count must be integers")
        if (
            self.config["min_referee_count"] < 0
            or self.config["max_referee_count"] < self.config["min_referee_count"]
        ):
            raise ValueError("Invalid min/max referee count values.")

        return True

    def find_schedule(
        self,
        use_saved_schedule=False,
        filename="saved_schedule.json",
        max_attempts=30000,
        num_cores=None,
    ):
        """
        Find a schedule using the instance's config and teams.
        Tries loading first, then generates using parallel processing if num_cores != 1.

        Args:
            use_saved_schedule (bool): Try loading from file first.
            filename (str): Path to the schedule file.
            max_attempts (int): Max generation attempts.
            num_cores (int, optional): Number of cores for parallel generation.
                                      Defaults to cpu_count(). Set to 1 for sequential.

        Returns:
            tuple: (schedule_data, total_attempts)
                   schedule_data is the formatted schedule (dict) or None if failed.
                   total_attempts is the number of attempts made during generation.
        """
        if use_saved_schedule:
            schedule_data = load_schedule_from_file(filename)
            if schedule_data is not None:
                print(f"Schedule loaded from {filename}")
                # Validate loaded schedule against current config? Optional but recommended.
                # valid_load, load_msg = self.validate_schedule(schedule_data) # Need to adapt validate for formatted data?
                # if valid_load: ...
                self.raw_schedule = (
                    None  # Indicate loaded, no raw internal format available
                )
                return schedule_data, 0
            else:  # File not found or empty
                print(
                    f"No schedule data found in {filename}. Generating new schedule..."
                )

        elif not use_saved_schedule:  # Explicitly told not to load
            print(f"Generating new schedule (use_saved_schedule=False)...")

        start_time = time.time()

        if num_cores is None:
            num_cores = cpu_count()
        num_cores = max(1, num_cores)  # Ensure at least 1

        print(f"Searching for valid schedule using {num_cores} cores...")
        self.raw_schedule = None  # Reset before attempts
        total_attempts = 0

        if num_cores == 1:
            print("Running sequentially...")
            for attempt in range(max_attempts):
                total_attempts += 1
                schedule = self.find_schedule_attempt()
                if schedule is not None:
                    self.raw_schedule = schedule
                    break
                if total_attempts % 50 == 0:
                    print(f"Attempted {total_attempts} schedules...")
        else:
            attempts_per_batch = max(1, num_cores * 2)
            # Pass self.config (pickleable dict) to the helper via args tuple
            args = [(self.config,)] * attempts_per_batch
            print(
                f"Running in parallel with {num_cores} workers (batch size: {attempts_per_batch})..."
            )
            max_batches = (max_attempts + attempts_per_batch - 1) // attempts_per_batch

            for batch_num in range(max_batches):
                if self.raw_schedule is not None:
                    break  # Found in previous batch

                current_batch_size = min(
                    attempts_per_batch, max_attempts - total_attempts
                )
                if current_batch_size <= 0:
                    break

                try:
                    with Pool(num_cores) as pool:
                        schedules = pool.starmap(
                            _run_find_schedule_attempt, args[:current_batch_size]
                        )
                    total_attempts += current_batch_size

                    for schedule in schedules:
                        if schedule is not None:
                            self.raw_schedule = schedule
                            print(
                                f"\nFound potential schedule after ~{total_attempts} attempts."
                            )
                            break  # Exit inner loop
                except Exception as e:
                    print(f"\nError during parallel execution: {e}")
                    print("Aborting parallel search.")
                    total_attempts = max_attempts  # Mark as failed
                    break  # Exit outer loop

                if (batch_num + 1) % 5 == 0 and self.raw_schedule is None:
                    print(f"Attempted {total_attempts} schedules...")
                if self.raw_schedule is not None:
                    break  # Exit outer loop

        end_time = time.time()
        elapsed_time = end_time - start_time

        if self.raw_schedule is None:
            print(
                f"\nNo valid schedule found after {total_attempts} attempts in {elapsed_time:.2f} seconds."
            )
            return None, total_attempts

        print(
            f"Schedule found after {total_attempts} attempts in {elapsed_time:.2f} seconds."
        )
        schedule_data = convert_to_formatted_schedule(
            self.raw_schedule, self.config["levels"], self.config
        )
        save_schedule_to_file(schedule_data, filename)
        print(f"Schedule saved to {filename}")

        return schedule_data, total_attempts


if __name__ == "__main__":
    # Define the config (or load from elsewhere)
    # Using the default defined earlier, but could override here:
    config = DEFAULT_CONFIG
    # Example override:
    # config["min_referee_count"] = 4
    # config["max_referee_count"] = 6
    # config["slot_limits"][1] = 3
    # Define filename (consider making this configurable via args)
    filename = os.path.join(os.path.dirname(__file__), "saved_schedule.json")

    scheduler = Scheduler(config)

    print("\nAttempting to find or generate schedule...")
    start_time = time.time()

    # Call the main method on the instance
    # use_saved_schedule=False forces generation
    # num_cores=1 forces sequential processing (easier debugging)
    # Set num_cores=None to use default (all cores) or specific number for parallel
    final_schedule_data, total_attempts = scheduler.find_schedule(
        use_saved_schedule=False,  # Try loading first
        filename=filename,
        max_attempts=30000,  # Reduced attempts for quicker testing
        num_cores=1,  # Use None for parallel, 1 for sequential
    )
    end_time = time.time()

    if final_schedule_data:
        # Schedule found (either loaded or generated)
        # print_schedule(final_schedule_data) # Optional: print the formatted schedule

        # Print statistics using the data from the scheduler instance
        print("\n--- Schedule Statistics ---")
        print_statistics(final_schedule_data, scheduler.teams, config["levels"], config)

        # Tests require the raw internal schedule format (stored in scheduler.raw_schedule)
        # Only run tests if a *new* schedule was generated (raw_schedule will exist)
        if scheduler.raw_schedule:
            print("\n--- Running Tests on Generated Schedule ---")
            raw_schedule = final_schedule_data
            levels = scheduler.config["levels"]
            teams_per_level = scheduler.config["teams_per_level"]
            courts_per_slot = scheduler.config["courts_per_slot"]
            num_slots = scheduler.config["num_slots"]
            first_half_weeks = scheduler.config["first_half_weeks"]

            pt = pairing_tests(raw_schedule, levels, teams_per_level)
            cpt = cycle_pairing_test(raw_schedule, levels, teams_per_level)
            rpt = referee_player_test(raw_schedule)
            ast = adjacent_slot_test(raw_schedule)
            gst = global_slot_distribution_test(
                raw_schedule, courts_per_slot, num_slots
            )
            mpt = mirror_pairing_test(
                raw_schedule, first_half_weeks=first_half_weeks
            )

            print("\nTest Results:")
            print(f"  Pairings correct: {pt}")
            print(f"  Cycle pairings: {cpt}")
            print(f"  No referee plays in their game: {rpt}")
            print(f"  Adjacent-slot condition: {ast}")
            print(f"  Global slot distribution: {gst}")
            print(f"  Mirror pairings: {mpt}")

    else:
        print("\nFailed to load or generate a valid schedule.")

    print(f"\nTotal generation attempts (if any): {total_attempts}")
