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

###########################
# Configuration Parameters
###########################

# Define the scheduling configuration
config = {
    # League structure
    "levels": ["A", "B", "C"],  # Names of the levels/divisions
    "teams_per_level": {  # Number of teams in each level
        "A": 6,
        "B": 6,
        "C": 6,
    },
    # Schedule structure
    "first_half_weeks": 5,  # Weeks in first half; second half will mirror these
    "total_weeks": 10,  # Total number of weeks in the season
    # Slots configuration
    "num_slots": 4,  # Number of time slots (1-indexed)
    "courts_per_slot": [
        1,
        3,
        2,
        3,
    ],  # Number of courts available in each slot (1-indexed)
    # Distributions for levels
    "distributions_list": [
        (1, 2, 2),  # low-slot distribution
        (2, 3, 4),  # middle distribution
        (3, 4, 4),  # high-slot distribution
    ],
    # Constraints for play balance
    "slot_limits": {
        1: 2,  # Teams can play at most 2 games in slot 1
        2: 6,  # Teams can play at most 6 games in slots 2 and 3
        3: 6,
        4: 4,  # Teams can play at most 4 games in slot 4
    },
    # Constraints for referee balance
    "min_referee_count": 3,  # Minimum times a team must referee in a season per level
    "max_referee_count": 6,  # Maximum times a team can referee in a season per level
    # Optimization priorities
    "priority_slots": [1, 4],  # Slots where balance is more important
    "priority_multiplier": 100,  # Extra weight for priority slots in balance calculations
}

# Derived parameters
levels = config["levels"]
first_half_weeks = config["first_half_weeks"]
total_weeks = config["total_weeks"]
distributions_list = config["distributions_list"]

# Get all teams as a list of integers for each level
teams = {}
all_teams = []
for level in levels:
    teams[level] = list(range(config["teams_per_level"][level]))
    all_teams.extend(teams[level])

###########################
# Parameters & Round-Robin
###########################

# The three available slot distributions.
# (When one level gets (1,2,2), another (2,3,4) and the third (3,4,4),
# the overall weekly capacities are met:
#  Slot 1: 1 game, Slot 2: 3 games, Slot 3: 2 games, Slot 4: 3 games.)


def generate_round_robin_pairings(n):
    """
    Generate a round-robin schedule for n teams using the circle method.
    Returns a list of rounds (each round is a list of games, where a game is a tuple of two team indices).
    For n even there will be n-1 rounds.
    """
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


# Generate fixed round-robin pairings for each level.
rr_pairings = {}
for level in levels:
    rr_pairings[level] = generate_round_robin_pairings(
        config["teams_per_level"][level]
    )  # 5 rounds for 6 teams

##########################################
# Candidate Referee Assignment Functions
##########################################


def candidate_referees_for_game(distribution, pairing, game_index):
    """
    For a given game (indexed by game_index, 0–2) in a week,
    return the list of teams eligible to referee that game.
    Eligibility:
      - The team is not playing in that game.
      - Its own playing game (from the pairing) is scheduled in a slot that differs by exactly 1.
    """
    team_to_game = {}
    for i, pair in enumerate(pairing):
        for t in pair:
            team_to_game[t] = i
    candidates = []
    slot = distribution[game_index]
    for t in range(config["teams_per_level"][level]):
        if t in pairing[game_index]:
            continue
        j = team_to_game[t]
        if abs(distribution[j] - slot) == 1:
            candidates.append(t)
    return candidates


def get_ref_assignment(distribution, pairing, current_ref_counts):
    """
    For a given pairing and slot distribution (each a 3-tuple for 3 games in a week),
    compute candidate referee assignments (a tuple of 3 teams) that satisfy:
      - Each referee is eligible per candidate_referees_for_game.
      - The 3 referees are distinct.
    If multiple assignments exist, choose the one minimizing the sum of current referee counts.
    Returns a tuple (r0, r1, r2) or None.
    """
    candidate_lists = []
    for i in range(3):
        candidates = candidate_referees_for_game(distribution, pairing, i)
        candidate_lists.append(candidates)
    valid_assignments = []
    for assignment in product(*candidate_lists):
        if len(set(assignment)) == 3:
            valid_assignments.append(assignment)
    if not valid_assignments:
        return None
    best = min(
        valid_assignments, key=lambda a: sum(current_ref_counts.get(t, 0) for t in a)
    )
    return best


############################################
# Backtracking Solver for Half Schedules
############################################


def solve_half_schedule(rr_pairings, weeks, initial_ref_counts=None):
    """
    Solve a half-schedule (for a given number of weeks) for each level.
    For each level and week, the pairing is fixed from rr_pairings[level][week].
    We assign a slot distribution (randomly shuffling distributions_list) to each level,
    then choose a valid referee assignment.
    Returns a schedule (list of week assignments) and final referee counts.
    Each week assignment is a dict mapping level to (distribution, pairing, ref_assignment).
    """
    if initial_ref_counts is None:
        ref_counts = {level: {t: 0 for t in teams[level]} for level in levels}
    else:
        ref_counts = {level: dict(initial_ref_counts[level]) for level in levels}
    schedule = [None] * weeks

    def backtrack(week):
        if week == weeks:
            return True
        dist_assignment = distributions_list[:]  # copy list
        random.shuffle(dist_assignment)
        week_assignment = {}
        new_ref_counts = {level: dict(ref_counts[level]) for level in levels}
        valid = True
        for i, level in enumerate(levels):
            distribution = dist_assignment[i]
            pairing = rr_pairings[level][week]  # fixed pairing for this week
            ref_assignment = get_ref_assignment(
                distribution, pairing, new_ref_counts[level]
            )
            if ref_assignment is None:
                valid = False
                break
            week_assignment[level] = (distribution, pairing, ref_assignment)
            for t in ref_assignment:
                new_ref_counts[level][t] += 1
        if not valid:
            return False
        schedule[week] = week_assignment
        old_ref_counts = {level: dict(ref_counts[level]) for level in levels}
        for level in levels:
            ref_counts[level] = new_ref_counts[level]
        if backtrack(week + 1):
            return True
        else:
            for level in levels:
                ref_counts[level] = old_ref_counts[level]
            return False

    if backtrack(0):
        return schedule, ref_counts
    else:
        return None, None


def solve_second_half(rr_pairings, first_half_schedule, initial_ref_counts):
    """
    Solve the second half of the schedule.
    For each level and week, the pairing is forced to be identical to that in the first half.
    We still randomize the slot distribution assignment.
    """
    weeks = first_half_weeks
    ref_counts = {level: dict(initial_ref_counts[level]) for level in levels}
    schedule = [None] * weeks

    def backtrack(week):
        if week == weeks:
            return True
        dist_assignment = distributions_list[:]
        random.shuffle(dist_assignment)
        week_assignment = {}
        new_ref_counts = {level: dict(ref_counts[level]) for level in levels}
        valid = True
        for i, level in enumerate(levels):
            distribution = dist_assignment[i]
            pairing = first_half_schedule[week][level][1]  # same pairing as first half
            ref_assignment = get_ref_assignment(
                distribution, pairing, new_ref_counts[level]
            )
            if ref_assignment is None:
                valid = False
                break
            week_assignment[level] = (distribution, pairing, ref_assignment)
            for t in ref_assignment:
                new_ref_counts[level][t] += 1
        if not valid:
            return False
        schedule[week] = week_assignment
        old_ref_counts = {level: dict(ref_counts[level]) for level in levels}
        for level in levels:
            ref_counts[level] = new_ref_counts[level]
        if backtrack(week + 1):
            return True
        else:
            for level in levels:
                ref_counts[level] = old_ref_counts[level]
            return False

    if backtrack(0):
        return schedule, ref_counts
    else:
        return None, None


##############################################
# Phase 1: Balance Team Play Counts (Post-Processing)
##############################################


def weighted_play_imbalance_metric(schedule):
    """
    Compute a weighted global imbalance metric based on configured limits.
    For each level and team for each slot, if the actual count exceeds the limit,
    add: violation_penalty * (count - limit)^2.
    For priority slots, multiply the penalty by an extra multiplier.
    Lower values indicate better balance.
    """
    play_counts = compute_team_play_counts(schedule)  # level -> {team -> {slot: count}}
    total = 0.0
    violation_penalty = 1e7  # Penalty factor for exceeding the limit

    for level in levels:
        for t in teams[level]:
            for s in range(1, config["num_slots"] + 1):
                count = play_counts[level][t][s]
                # Get limit from config
                limit = config["slot_limits"].get(s, float("inf"))

                if count > limit:
                    # Apply extra multiplier for priority slots
                    if s in config["priority_slots"]:
                        total += (
                            violation_penalty
                            * config["priority_multiplier"]
                            * (count - limit) ** 2
                        )
                    else:
                        total += violation_penalty * (count - limit) ** 2
    return total


def balance_playing_slots(
    schedule, max_iter=10000, initial_temp=1.0, cooling_rate=0.01
):
    """
    Balance the playing slots while preserving the round-robin structure.
    Only changes slot distributions and their ordering, never modifies pairings.
    """
    new_schedule = copy.deepcopy(schedule)
    current_cost = weighted_play_imbalance_metric(new_schedule)
    temp = initial_temp
    first_half = first_half_weeks

    for it in range(max_iter):
        # Instead of deep copying the entire schedule, we'll just track and modify the specific changed elements
        week = random.randrange(len(new_schedule))
        level1, level2 = random.sample(levels, 2)

        # Get original information
        dist1, pairing1, ref1 = new_schedule[week][level1]
        dist2, pairing2, ref2 = new_schedule[week][level2]

        # Compute new referee assignments
        new_ref1 = get_ref_assignment(dist2, pairing1, {t: 0 for t in teams[level1]})
        new_ref2 = get_ref_assignment(dist1, pairing2, {t: 0 for t in teams[level2]})

        # Only proceed if valid referee assignments exist
        if not (new_ref1 and new_ref2):
            continue

        # Check if the swap would maintain valid distributions before modifying the schedule
        # Create temporary assignment just to check validity
        temp_week = dict(new_schedule[week])
        temp_week[level1] = (dist2, pairing1, new_ref1)
        temp_week[level2] = (dist1, pairing2, new_ref2)

        # Apply changes to a temporary schedule for evaluation
        candidate_schedule = [
            week_data if i != week else temp_week
            for i, week_data in enumerate(new_schedule)
        ]

        # Calculate cost of new schedule
        candidate_cost = weighted_play_imbalance_metric(candidate_schedule)
        delta = candidate_cost - current_cost

        # Accept move based on simulated annealing criteria
        if delta < 0 or random.random() < math.exp(-delta / temp):
            # Only if we accept the move, actually update the schedule
            new_schedule[week][level1] = (dist2, pairing1, new_ref1)
            new_schedule[week][level2] = (dist1, pairing2, new_ref2)
            current_cost = candidate_cost

        # Cool temperature
        temp = initial_temp * math.exp(-cooling_rate * it)
        if temp < 1e-6:
            break

    return new_schedule


def compute_team_play_counts(schedule):
    """
    For each level, compute a dict: team -> {slot: count} of playing appearances.
    Each game in a week (for a level) contributes 1 appearance in its slot for each team playing.
    """
    counts = {
        level: {
            t: {s: 0 for s in range(1, config["num_slots"] + 1)} for t in teams[level]
        }
        for level in levels
    }
    for week in schedule:
        for level in week:
            distribution, pairing, _ = week[level]
            for i in range(len(pairing)):
                slot = distribution[i]
                t1, t2 = pairing[i]
                counts[level][t1][slot] += 1
                counts[level][t2][slot] += 1
    return counts


##############################################
# Phase 2: Referee Post-Processing
##############################################


def compute_overall_ref_counts(schedule):
    counts = {level: {t: 0 for t in teams[level]} for level in levels}
    for week in schedule:
        for level in week:
            _, _, ref_assignment = week[level]
            for r in ref_assignment:
                counts[level][r] += 1
    return counts


#####################################
# Local Moves for Referee Balancing (Swapping Games)
#####################################


def move_ref_games_schedule(schedule, max_iterations=150):
    """
    Improve referee balance using a more aggressive optimization approach
    that still preserves the round-robin property and mirror relationships.
    """
    new_schedule = copy.deepcopy(schedule)
    from itertools import permutations as iter_permutations

    def total_ref_imbalance(ref_counts):
        """Calculate referee imbalance with higher penalties for outliers"""
        teams_list = list(range(config["teams_per_level"][level]))
        values = [ref_counts.get(t, 0) for t in teams_list]
        mean = sum(values) / len(values)
        # Use squared differences to penalize outliers more heavily
        return sum((x - mean) ** 2 for x in values)

    def week_distribution_ok(week):
        dists = set(week[level][0] for level in week)
        return dists == set(distributions_list)

    # Track the global pairings to make sure we don't disrupt the round-robin
    global_pairings = {level: set() for level in levels}
    for w in range(first_half_weeks):
        for level in levels:
            _, pairing, _ = new_schedule[w][level]
            for pair in pairing:
                global_pairings[level].add(tuple(sorted(pair)))

    overall = compute_overall_ref_counts(new_schedule)
    current_imbalance = {level: total_ref_imbalance(overall[level]) for level in levels}

    # Try more iterations to find better solutions
    for iteration in range(max_iterations):
        made_improvement = False

        # Try swapping weeks completely for first half
        for w1, w2 in random.sample(
            list(product(range(first_half_weeks), repeat=2)),
            min(10, first_half_weeks**2),
        ):
            if w1 == w2:
                continue

            for level in levels:
                # Instead of deep copying the entire schedule, only store the values that will change
                orig_w1_data = new_schedule[w1][level]
                orig_w2_data = new_schedule[w2][level]

                # Temporarily swap
                new_schedule[w1][level] = orig_w2_data
                new_schedule[w2][level] = orig_w1_data

                # Update mirror weeks if needed
                mirror_w1, mirror_w2 = w1 + first_half_weeks, w2 + first_half_weeks
                orig_mirror1_data = None
                orig_mirror2_data = None

                if mirror_w1 < len(new_schedule) and mirror_w2 < len(new_schedule):
                    # Save mirror week data
                    orig_mirror1_data = new_schedule[mirror_w1][level]
                    orig_mirror2_data = new_schedule[mirror_w2][level]

                    # Swap mirror weeks
                    new_schedule[mirror_w1][level] = orig_mirror2_data
                    new_schedule[mirror_w2][level] = orig_mirror1_data

                # Check if all weeks have valid distributions
                valid = True
                for w in [w1, w2, mirror_w1, mirror_w2]:
                    if w < len(new_schedule) and not week_distribution_ok(
                        new_schedule[w]
                    ):
                        valid = False
                        break

                # Calculate new balance only if the change is valid
                if valid:
                    new_overall = compute_overall_ref_counts(new_schedule)
                    new_imbalance = total_ref_imbalance(new_overall[level])

                    # Accept if improved
                    if new_imbalance < current_imbalance[level]:
                        overall = new_overall
                        current_imbalance[level] = new_imbalance
                        made_improvement = True
                        break

                # Revert changes if not accepted or not valid
                if not (valid and new_imbalance < current_imbalance[level]):
                    new_schedule[w1][level] = orig_w1_data
                    new_schedule[w2][level] = orig_w2_data

                    if orig_mirror1_data is not None:
                        new_schedule[mirror_w1][level] = orig_mirror1_data
                        new_schedule[mirror_w2][level] = orig_mirror2_data

            if made_improvement:
                break

        # Try all permutations of slot distributions within a week
        if not made_improvement:
            w = random.randrange(first_half_weeks)
            level = random.choice(levels)

            distribution, pairing, _ = new_schedule[w][level]

            # Try different permutations of the slot distribution
            for new_dist in random.sample(
                list(iter_permutations(distribution)),
                min(6, len(list(iter_permutations(distribution)))),
            ):
                if new_dist == distribution:
                    continue

                # Calculate new ref assignment
                temp_overall = copy.deepcopy(overall)
                # Remove current refs from count
                for r in new_schedule[w][level][2]:
                    temp_overall[level][r] -= 1

                new_ref = get_ref_assignment(new_dist, pairing, temp_overall[level])
                if new_ref is None:
                    continue

                # Update temporary counts
                for r in new_ref:
                    temp_overall[level][r] += 1

                # Check if this improves balance
                new_imbalance = total_ref_imbalance(temp_overall[level])
                if new_imbalance < current_imbalance[level]:
                    # Apply the change
                    new_schedule[w][level] = (new_dist, pairing, new_ref)

                    # Handle mirror week if needed - FIX: keep same pairing in mirror week
                    mirror_w = w + first_half_weeks
                    if mirror_w < len(new_schedule):
                        mirror_dist = new_schedule[mirror_w][level][0]
                        # Use the same pairing as week w to maintain mirror relationship
                        mirror_ref = get_ref_assignment(
                            mirror_dist, pairing, {t: 0 for t in teams[level]}
                        )

                        if mirror_ref is not None:
                            new_schedule[mirror_w][level] = (
                                mirror_dist,
                                pairing,  # Keep the same pairing to maintain mirror relationship
                                mirror_ref,
                            )
                        else:
                            continue

                    # Verify week distributions
                    if not week_distribution_ok(new_schedule[w]) or (
                        mirror_w < len(new_schedule)
                        and not week_distribution_ok(new_schedule[mirror_w])
                    ):
                        continue

                    # Update overall counts and imbalance
                    overall = compute_overall_ref_counts(new_schedule)
                    current_imbalance[level] = new_imbalance
                    made_improvement = True
                    break

        # Early termination if no improvements
        if not made_improvement:
            # Once in a while, try a random change to escape local minimum
            if iteration % 100 == 0:
                # Just recompute all ref assignments for a week using the global state
                w = random.randrange(first_half_weeks)
                for level in levels:
                    distribution, pairing, _ = new_schedule[w][level]
                    new_ref = get_ref_assignment(distribution, pairing, overall[level])
                    if new_ref:
                        new_schedule[w][level] = (distribution, pairing, new_ref)

                # Update overall stats
                overall = compute_overall_ref_counts(new_schedule)
                current_imbalance = {
                    level: total_ref_imbalance(overall[level]) for level in levels
                }
            else:
                # After many iterations with no improvement, break
                if iteration > max_iterations // 2:
                    break

    return new_schedule


#########################################
# Run Post-Processing Phases & Testing
#########################################


def validate_schedule(schedule, teams, levels):
    """
    Validate schedule against configured limits:
    1. Teams must referee between min_referee_count and max_referee_count times in any level
    2. Teams must play within the configured slot limits
    Returns (bool, str) - (is_valid, error_message)
    """
    # Check referee counts
    ref_counts = {level: {t: 0 for t in teams[level]} for level in levels}
    for week in schedule:
        for level in week:
            _, _, ref_assignment = week[level]
            for r in ref_assignment:
                ref_counts[level][r] += 1

    min_ref = config["min_referee_count"]
    max_ref = config["max_referee_count"]

    for level in levels:
        for team in teams[level]:
            if ref_counts[level][team] > max_ref or ref_counts[level][team] < min_ref:
                return (
                    False,
                    f"Team {team+1} referees {ref_counts[level][team]} times in level {level} "
                    f"(should be between {min_ref} and {max_ref})",
                )

    # Check slot limits
    play_counts = {
        level: {
            t: {s: 0 for s in range(1, config["num_slots"] + 1)} for t in teams[level]
        }
        for level in levels
    }
    for week in schedule:
        for level in week:
            distribution, pairing, _ = week[level]
            for i, slot in enumerate(distribution):
                t1, t2 = pairing[i]
                play_counts[level][t1][slot] += 1
                play_counts[level][t2][slot] += 1

    for level in levels:
        for team in teams[level]:
            for slot, limit in config["slot_limits"].items():
                if play_counts[level][team][slot] > limit:
                    return (
                        False,
                        f"Team {team+1} plays {play_counts[level][team][slot]} times in slot {slot} "
                        f"in level {level} (max is {limit})",
                    )

    return True, "Schedule is valid"


def find_schedule_attempt():
    """Single attempt to find a valid schedule"""
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

    # print("Phase 1: Balancing global slot distribution...")
    final_schedule = balance_playing_slots(full_schedule)

    # print("Phase 2: Local moves to improve referee balance (swapping games)...")
    final_schedule = move_ref_games_schedule(final_schedule)

    # Validate the schedule
    is_valid, message = validate_schedule(final_schedule, teams, levels)
    print(message)
    if is_valid:
        return final_schedule
    return None


def find_schedule(
    use_saved_schedule=True,
    filename="saved_schedule.json",
    max_attempts=10000,
    num_cores=14,
):
    """
    Find a schedule by first trying to load from a file, then generating a new one if needed.
    Uses parallel processing for generation.

    Args:
        filename (str): Path to the saved schedule file
        max_attempts (int): Maximum number of attempts to find a valid schedule
        num_cores (int): Number of cores to use for parallel processing. Defaults to all available.

    Returns:
        dict: The formatted schedule data
    """

    if use_saved_schedule:
        # First try to load a saved schedule
        schedule_data = load_schedule_from_file(filename)

        # If schedule exists in file, return it
        if schedule_data is not None:
            print(f"Schedule loaded from {filename}")
            return schedule_data

    # Otherwise, generate a new schedule using multiprocessing
    if not use_saved_schedule:
        print(f"No schedule found in {filename}. Generating new schedule...")
    start_time = time.time()

    if num_cores is None:
        num_cores = cpu_count()

    print(f"Searching for valid schedule using {num_cores} cores...")
    attempts_per_batch = num_cores

    raw_schedule = None

    for attempt in range(0, max_attempts, attempts_per_batch):
        with Pool(num_cores) as pool:
            schedules = pool.starmap(find_schedule_attempt, [()] * attempts_per_batch)
            for schedule in schedules:
                if schedule is not None:
                    raw_schedule = schedule
                    break

        if raw_schedule is not None:
            break

        # Print progress every few batches
        if (attempt // attempts_per_batch) % 10 == 0:
            print(f"Attempted {attempt + attempts_per_batch} schedules...")

    if raw_schedule is None:
        print(f"\nNo valid schedule found after {max_attempts} attempts")
        return None

    # Format and save the successful schedule
    end_time = time.time()
    print(f"Schedule found in {end_time - start_time:.2f} seconds")

    # Convert to the standardized JSON format
    schedule_data = convert_to_formatted_schedule(raw_schedule, levels)

    # Save the newly generated schedule
    save_schedule_to_file(schedule_data, filename)
    print(f"Schedule saved to {filename}")

    return schedule_data


if __name__ == "__main__":
    from tests import (
        pairing_tests,
        global_slot_distribution_test,
        referee_player_test,
        adjacent_slot_test,
        mirror_pairing_test,
    )
    from stats import print_statistics

    filename = "/home/platelminto/Documents/dev/usbf-schedule/saved_schedule.json"

    print("Generating new schedule...")
    start_time = time.time()
    final_schedule = find_schedule(use_saved_schedule=False)
    end_time = time.time()

    if final_schedule:
        print(f"Schedule found in {end_time - start_time:.2f} seconds")

    if final_schedule:
        print_schedule(final_schedule)
        print("\nRunning tests on final schedule:")
        pt = pairing_tests(final_schedule, levels, teams)
        rpt = referee_player_test(final_schedule)
        ast = adjacent_slot_test(final_schedule)
        gst = global_slot_distribution_test(final_schedule)
        mpt = mirror_pairing_test(final_schedule)

        # Pass the config to print_statistics
        print_statistics(final_schedule, teams, levels, config)

        print("\nTest Results:")
        print(f"  Pairings correct: {pt}")
        print(f"  No referee plays in their game: {rpt}")
        print(f"  Adjacent-slot condition: {ast}")
        print(f"  Global slot distribution: {gst}")
        print(f"  Mirror pairings: {mpt}")
    else:
        print("Failed to generate a valid schedule.")
