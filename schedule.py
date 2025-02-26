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
    # "distributions_list": [
    #     (1, 2, 2),  # low-slot distribution
    #     (2, 3, 4),  # middle distribution
    #     (3, 4, 4),  # high-slot distribution
    # ],
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

levels = config["levels"]
# For each level, create teams as 0-indexed integers.
teams = {level: list(range(config["teams_per_level"][level])) for level in levels}


#############################################
# Candidate Slot Assignment (per level)
#############################################

def generate_level_slot_assignments(level, num_games):
    """
    Generate candidate slot assignments for a level's round (num_games games).
    Each candidate is a tuple of length num_games with values in {1,...,config["num_slots"]}.
    
    Local constraints:
      - For each slot s, the number of games assigned to s is <= (teams-1)//2.
      - There must be at least 2 distinct slots used.
      - The set of slots used must be contiguous (e.g. {2,3} is okay; {1,3} is not).
    """
    assignments = []
    num_slots = config["num_slots"]
    max_local = (config["teams_per_level"][level] - 1) // 2  # e.g., for 6 teams, max 2 games per slot.
    for candidate in product(range(1, num_slots + 1), repeat=num_games):
        # Check local capacity constraint for each slot.
        if any(candidate.count(s) > max_local for s in range(1, num_slots + 1)):
            continue
        # Require at least 2 distinct slots (to allow adjacent-slot referee assignment).
        slots_used = sorted(set(candidate))
        if len(slots_used) < 2:
            continue
        # Check that the used slots are contiguous.
        if slots_used[-1] - slots_used[0] != len(slots_used) - 1:
            continue
        assignments.append(candidate)
    return assignments

#############################################
# Candidate Referee Assignment Functions
#############################################

def candidate_referees_for_game(level, slot_assignment, pairing, game_index):
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
    for t in range(config["teams_per_level"][level]):
        if t in pairing[game_index]:
            continue
        j = team_to_game[t]
        if abs(slot_assignment[j] - slot) == 1:
            candidates.append(t)
    return candidates

def get_ref_assignment(level, slot_assignment, pairing, current_ref_counts):
    """
    Given a slot_assignment for a round (a tuple of slots for each game) and
    fixed pairings, return a tuple of referee assignments (one per game) that:
      - Each referee is eligible per candidate_referees_for_game.
      - The referees are distinct.
    If multiple valid assignments exist, choose one minimizing the sum of current referee counts.
    """
    candidate_lists = []
    for i in range(len(pairing)):
        candidates = candidate_referees_for_game(level, slot_assignment, pairing, i)
        candidate_lists.append(candidates)
    valid_assignments = []
    for assignment in product(*candidate_lists):
        if len(set(assignment)) == len(assignment):
            valid_assignments.append(assignment)
    if not valid_assignments:
        return None
    best = min(valid_assignments, key=lambda a: sum(current_ref_counts.get(t, 0) for t in a))
    return best

#############################################
# Backtracking Solver for Half Schedules (Direct Slot Assignment)
#############################################

def solve_half_schedule(rr_pairings, weeks, initial_ref_counts=None):
    """
    For each week, for each level assign a candidate slot assignment (and corresponding referee assignment)
    that meets both local and global constraints.
    
    Global constraints (per week):
      - The sum of games assigned to a slot (across levels) does not exceed the courts available in that slot.
    """
    if initial_ref_counts is None:
        ref_counts = {level: {t: 0 for t in teams[level]} for level in levels}
    else:
        ref_counts = {level: dict(initial_ref_counts[level]) for level in levels}
    schedule = [None] * weeks

    def backtrack(week):
        if week == weeks:
            return True
        # Global usage per slot for this week.
        global_usage = {s: 0 for s in range(1, config["num_slots"] + 1)}
        week_assignment = {}
        # Copy referee counts to update as we assign each level.
        new_ref_counts = {level: dict(ref_counts[level]) for level in levels}

        def assign_level(i, current_usage):
            if i == len(levels):
                return True
            level = levels[i]
            pairing = rr_pairings[level][week]  # Fixed round-robin pairing for this level.
            num_games = len(pairing)
            candidate_assignments = generate_level_slot_assignments(level, num_games)
            random.shuffle(candidate_assignments)
            for slot_assignment in candidate_assignments:
                # Count how many games in each slot for this candidate.
                candidate_count = {s: slot_assignment.count(s) for s in range(1, config["num_slots"] + 1)}
                # Check global capacity: for each slot, usage + candidate_count <= courts available.
                feasible = True
                for s in range(1, config["num_slots"] + 1):
                    if current_usage[s] + candidate_count.get(s, 0) > config["courts_per_slot"][s - 1]:
                        feasible = False
                        break
                if not feasible:
                    continue
                # Try to get a referee assignment for this candidate.
                ref_assignment = get_ref_assignment(level, slot_assignment, pairing, new_ref_counts[level])
                if ref_assignment is None:
                    continue
                # Update current usage.
                for s in range(1, config["num_slots"] + 1):
                    current_usage[s] += candidate_count.get(s, 0)
                week_assignment[level] = (slot_assignment, pairing, ref_assignment)
                for t in ref_assignment:
                    new_ref_counts[level][t] += 1
                # Recurse to the next level.
                if assign_level(i + 1, current_usage):
                    return True
                # Backtrack.
                for s in range(1, config["num_slots"] + 1):
                    current_usage[s] -= candidate_count.get(s, 0)
                del week_assignment[level]
                for t in ref_assignment:
                    new_ref_counts[level][t] -= 1
            return False

        if not assign_level(0, global_usage):
            return False
        schedule[week] = week_assignment
        for level in levels:
            ref_counts[level] = new_ref_counts[level]
        return backtrack(week + 1)

    if backtrack(0):
        return schedule, ref_counts
    else:
        return None, None

#############################################
# Example Round-Robin Generation (for testing)
#############################################

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

def solve_second_half(rr_pairings, first_half_schedule, initial_ref_counts):
    """
    Solve the second half of the schedule.
    
    For each level and week (in the second half), we use the pairing from the
    corresponding week in the first half (to preserve the mirror property).
    We then assign slots (and corresponding referee assignments) using the same
    direct game-by-game backtracking approach with global usage constraints.
    """
    weeks = config["first_half_weeks"]
    ref_counts = {level: dict(initial_ref_counts[level]) for level in levels}
    schedule = [None] * weeks

    def backtrack(week):
        if week == weeks:
            return True
        global_usage = {s: 0 for s in range(1, config["num_slots"] + 1)}
        week_assignment = {}
        new_ref_counts = {level: dict(ref_counts[level]) for level in levels}

        def assign_level(i, current_usage):
            if i == len(levels):
                return True
            level = levels[i]
            # Use the pairing from the first half schedule for this level and week.
            pairing = first_half_schedule[week][level][1]
            num_games = len(pairing)
            candidate_assignments = generate_level_slot_assignments(level, num_games)
            random.shuffle(candidate_assignments)
            for slot_assignment in candidate_assignments:
                # Count how many games in each slot this candidate assignment would add.
                candidate_count = {s: slot_assignment.count(s) for s in range(1, config["num_slots"] + 1)}
                # Check that global capacity is not exceeded.
                feasible = True
                for s in range(1, config["num_slots"] + 1):
                    if current_usage[s] + candidate_count.get(s, 0) > config["courts_per_slot"][s - 1]:
                        feasible = False
                        break
                if not feasible:
                    continue
                # Try to assign referees given this candidate slot assignment.
                ref_assignment = get_ref_assignment(level, slot_assignment, pairing, new_ref_counts[level])
                if ref_assignment is None:
                    continue
                # If successful, update current usage and referee counts.
                for s in range(1, config["num_slots"] + 1):
                    current_usage[s] += candidate_count.get(s, 0)
                week_assignment[level] = (slot_assignment, pairing, ref_assignment)
                for t in ref_assignment:
                    new_ref_counts[level][t] += 1
                # Proceed to the next level.
                if assign_level(i + 1, current_usage):
                    return True
                # Backtrack.
                for s in range(1, config["num_slots"] + 1):
                    current_usage[s] -= candidate_count.get(s, 0)
                del week_assignment[level]
                for t in ref_assignment:
                    new_ref_counts[level][t] -= 1
            return False

        if not assign_level(0, global_usage):
            return False
        schedule[week] = week_assignment
        for level in levels:
            ref_counts[level] = new_ref_counts[level]
        return backtrack(week + 1)

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


def balance_playing_slots(schedule, max_iter=10000, initial_temp=1.0, cooling_rate=0.01):
    new_schedule = copy.deepcopy(schedule)
    current_cost = weighted_play_imbalance_metric(new_schedule)
    temp = initial_temp

    for it in range(max_iter):
        week = random.randrange(len(new_schedule))
        level1, level2 = random.sample(levels, 2)

        dist1, pairing1, ref1 = new_schedule[week][level1]
        dist2, pairing2, ref2 = new_schedule[week][level2]

        new_ref1 = get_ref_assignment(level1, dist2, pairing1, {t: 0 for t in teams[level1]})
        new_ref2 = get_ref_assignment(level2, dist1, pairing2, {t: 0 for t in teams[level2]})
        if not (new_ref1 and new_ref2):
            continue

        new_schedule[week][level1] = (dist2, pairing1, new_ref1)
        new_schedule[week][level2] = (dist1, pairing2, new_ref2)
        candidate_cost = weighted_play_imbalance_metric(new_schedule)
        delta = candidate_cost - current_cost

        if delta < 0 or random.random() < math.exp(-delta / temp):
            current_cost = candidate_cost
        else:
            new_schedule[week][level1] = (dist1, pairing1, ref1)
            new_schedule[week][level2] = (dist2, pairing2, ref2)

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



def total_ref_imbalance(level, ref_counts):
    """Compute the variance of referee counts for a given level."""
    team_list = list(range(config["teams_per_level"][level]))
    values = [ref_counts.get(t, 0) for t in team_list]
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values)

def is_week_global_valid(week_assignment):
    """
    Check that for the given week assignment (a dict mapping level -> (slot_assignment, pairing, ref_assignment)),
    the total number of games assigned to each slot exactly equals the expected value from config["courts_per_slot"].
    """
    usage = {s: 0 for s in range(1, config["num_slots"] + 1)}
    for level in week_assignment:
        slot_assignment, _, _ = week_assignment[level]
        for s in slot_assignment:
            usage[s] += 1
    for s in usage:
        if usage[s] != config["courts_per_slot"][s - 1]:
            return False
    return True

def composite_objective_no_global(schedule, weight_play=1.0, weight_ref=1.0):
    """
    Compute the composite objective from play imbalance and referee imbalance only.
    (Global slot distribution is now enforced as a hard constraint.)
    """
    play_cost = weighted_play_imbalance_metric(schedule)
    overall = compute_overall_ref_counts(schedule)
    ref_cost = 0
    for level in levels:
        ref_cost += total_ref_imbalance(level, overall[level])
    return weight_play * play_cost + weight_ref * ref_cost

def balance_schedule(schedule, max_iterations=300, weight_play=1.0, weight_ref=10.0):
    """
    Merged local search that improves play and referee balance while enforcing a hard
    global slot distribution constraint. Any move that causes a week's slot usage to deviate
    from config["courts_per_slot"] is rejected.
    """
    new_schedule = copy.deepcopy(schedule)
    current_obj = composite_objective_no_global(new_schedule, weight_play, weight_ref)
    
    for iteration in range(max_iterations):
        candidate_schedule = copy.deepcopy(new_schedule)
        move_type = random.choice(["candidate", "swap"])
        
        if move_type == "swap":
            # Swap move: choose two different weeks and one level; swap their assignments (and mirror weeks)
            w1, w2 = random.sample(range(config["first_half_weeks"]), 2)
            level = random.choice(levels)
            
            # Swap the assignments in the first half.
            orig_w1 = candidate_schedule[w1][level]
            orig_w2 = candidate_schedule[w2][level]
            candidate_schedule[w1][level] = orig_w2
            candidate_schedule[w2][level] = orig_w1
            
            # Swap the mirror weeks as well.
            mirror_w1 = w1 + config["first_half_weeks"]
            mirror_w2 = w2 + config["first_half_weeks"]
            if mirror_w1 < len(candidate_schedule) and mirror_w2 < len(candidate_schedule):
                orig_m1 = candidate_schedule[mirror_w1][level]
                orig_m2 = candidate_schedule[mirror_w2][level]
                candidate_schedule[mirror_w1][level] = orig_m2
                candidate_schedule[mirror_w2][level] = orig_m1
            
            # Enforce the hard global constraint: check affected weeks.
            if not (is_week_global_valid(candidate_schedule[w1]) and 
                    is_week_global_valid(candidate_schedule[w2]) and
                    (mirror_w1 >= len(candidate_schedule) or is_week_global_valid(candidate_schedule[mirror_w1])) and 
                    (mirror_w2 >= len(candidate_schedule) or is_week_global_valid(candidate_schedule[mirror_w2]))):
                continue
        
        else:  # candidate move
            # Candidate move: for a random week and level, try a new slot assignment.
            w = random.randrange(config["first_half_weeks"])
            level = random.choice(levels)
            current_assignment, pairing, _ = candidate_schedule[w][level]
            candidates = generate_level_slot_assignments(level, len(pairing))
            candidates = [a for a in candidates if a != current_assignment]
            if not candidates:
                continue
            new_assignment = random.choice(candidates)
            new_ref = get_ref_assignment(level, new_assignment, pairing, {t: 0 for t in teams[level]})
            if new_ref is None:
                continue
            candidate_schedule[w][level] = (new_assignment, pairing, new_ref)
            
            mirror_w = w + config["first_half_weeks"]
            if mirror_w < len(candidate_schedule):
                mirror_assignment, mirror_pairing, _ = candidate_schedule[mirror_w][level]
                mirror_ref = get_ref_assignment(level, mirror_assignment, mirror_pairing, {t: 0 for t in teams[level]})
                if mirror_ref is None:
                    continue
                candidate_schedule[mirror_w][level] = (mirror_assignment, mirror_pairing, mirror_ref)
            
            # Check that the modified week (and mirror) still have the exact global slot usage.
            if not is_week_global_valid(candidate_schedule[w]) or \
               (mirror_w < len(candidate_schedule) and not is_week_global_valid(candidate_schedule[mirror_w])):
                continue
        
        candidate_obj = composite_objective_no_global(candidate_schedule, weight_play, weight_ref)
        if candidate_obj < current_obj:
            new_schedule = candidate_schedule
            current_obj = candidate_obj
            # Optionally, print progress: 
            # print(f"Iteration {iteration}: improved objective to {current_obj:.2f}")
    
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
    
    final_schedule = balance_schedule(full_schedule)

    # Validate the schedule
    is_valid, message = validate_schedule(final_schedule, teams, levels)
    print(message)
    if is_valid:
        return final_schedule
    return None


def find_schedule(
    use_saved_schedule=True,
    filename="saved_schedule.json",
    max_attempts=100,
    num_cores=1,
):
    """
    Find a schedule by first trying to load from a file, then generating a new one if needed.
    Uses parallel processing for generation when num_cores > 1.

    Args:
        filename (str): Path to the saved schedule file
        max_attempts (int): Maximum number of attempts to find a valid schedule
        num_cores (int): Number of cores to use for parallel processing. Defaults to 1.

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
    raw_schedule = None

    if num_cores == 1:
        # Sequential approach for single core
        for attempt in range(max_attempts):
            schedule = find_schedule_attempt()
            if schedule is not None:
                raw_schedule = schedule
                break
                
            # Print progress every few attempts
            if attempt > 0 and attempt % 10 == 0:
                print(f"Attempted {attempt} schedules...")
    else:
        # Parallel approach for multiple cores
        attempts_per_batch = num_cores
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
