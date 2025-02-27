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

###########################
# Configuration Parameters
###########################

# Define the scheduling configuration
config = {
    # League structure
    "levels": ["A", "B", "C"],  # Names of the levels/divisions
    "teams_per_level": {  # Number of teams in each level
        "A": 4,
        "B": 6,
        "C": 6,
    },
    # Schedule structure
    "courts_per_slot": {
        # 1: 1,
        1: 3,
        2: 2,
        3: 3,
    },  # Number of courts available in each slot (1-indexed)
    # Distributions for levels
    # "distributions_list": [
    #     (1, 2, 2),  # low-slot distribution
    #     (2, 3, 4),  # middle distribution
    #     (3, 4, 4),  # high-slot distribution
    # ],
    # Constraints for play balance
    # These are the maximum number of games a team can play in a slot for the whole season.
    "slot_limits": {
        # 1: 2,  # Teams can play at most 2 games in slot 1
        1: 6,  # Teams can play at most 6 games in slots 2 and 3
        2: 6,
        3: 6,  # Teams can play at most 4 games in slot 4
    },
    # Constraints for referee balance
    "min_referee_count": 3,  # Minimum times a team must referee in a season per level
    "max_referee_count": 7,  # Maximum times a team can referee in a season per level
    # Optimization priorities
    "priority_slots": [3],  # Slots where balance is more important
    "priority_multiplier": 100,  # Extra weight for priority slots in balance calculations
}

# Instead of storing first_half_weeks, define season length based on max teams.
max_teams = max(config["teams_per_level"].values())
config.update({
    "total_weeks": 2 * (max_teams - 1),  # Season length defined by the level with most teams.
    "num_slots": len(config["courts_per_slot"]),
})


# Derived parameters
levels = config["levels"]

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


#############################################
# 1. Round-Robin Generation with Mirror Mapping
#############################################

def generate_mirrored_rr_schedule(n, total_weeks):
    """
    For n teams (even), generate a base round-robin (n-1 rounds) and a mirror mapping.
    mirror_mapping[r] is the list of week indices that use round index r.
    """
    base = generate_round_robin_pairings(n)  # base cycle (length = n-1)
    cycle_len = len(base)
    num_full_cycles = total_weeks // cycle_len
    remainder = total_weeks % cycle_len

    mirror_mapping = {}
    # For full cycles:
    for r in range(cycle_len):
        mirror_mapping[r] = [cycle * cycle_len + r for cycle in range(num_full_cycles)]
    # For the extra (partial) cycle, add rounds 0..remainder-1:
    for r in range(remainder):
        mirror_mapping.setdefault(r, []).append(num_full_cycles * cycle_len + r)
    return base, mirror_mapping

# For each level, compute the base pairings and mirror groups.
rr_pairings = {}
mirror_mappings = {}
for level in levels:
    n = config["teams_per_level"][level]
    base_pairings, mirror_mapping = generate_mirrored_rr_schedule(n, config["total_weeks"])
    rr_pairings[level] = base_pairings
    mirror_mappings[level] = mirror_mapping



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
      - For each slot s, the number of games assigned to s is <= teams//3.
      - There must be at least 2 distinct slots used.
      - The set of slots used must be contiguous (e.g. {2,3} is okay; {1,3} is not).
    """
    assignments = []
    num_slots = config["num_slots"]
    num_teams = config["teams_per_level"][level]
    max_local = num_teams // 3  # Each game needs 2 teams playing + 1 team refereeing

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
    # Get candidate lists first
    candidate_lists = []
    for i in range(len(pairing)):
        candidates = candidate_referees_for_game(level, slot_assignment, pairing, i)
        # Early exit: if any game has no candidates, no valid assignment exists
        if not candidates:
            return None
        candidate_lists.append(candidates)

    # Try a greedy approach first - this might give a good enough solution quickly
    num_teams = config["teams_per_level"][level]
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
            if not used[referee]:
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
    for assignment in product(*candidate_lists):
        if len(set(assignment)) == len(assignment):  # Ensure referees are distinct
            valid_assignments.append(assignment)
            scores.append(sum(current_ref_counts.get(t, 0) for t in assignment))

    if not valid_assignments:
        return None
    return valid_assignments[scores.index(min(scores))]


#############################################
# Backtracking Solver for Half Schedules (Direct Slot Assignment)
#############################################


#############################################
# Unified Solver for Full Season Schedule
#############################################

#############################################
# 2. Unified Solver With Mirror Requirements
#############################################

def reconstruct_schedule(assignments, mirror_mappings, total_weeks, levels):
    """
    Reconstruct full schedule (list of weeks, each mapping level -> (slot_assignment, pairing, ref_assignment))
    from the assignments per mirror group.
    """
    full_schedule = [{} for _ in range(total_weeks)]
    for level in levels:
        for r, weeks_list in mirror_mappings[level].items():
            if (level, r) in assignments:
                for w in weeks_list:
                    full_schedule[w][level] = assignments[(level, r)]
    return full_schedule

def compute_global_penalty(schedule, penalty_factor=1e9):
    """
    For each week and slot, add a penalty if the number of games in that slot
    does not equal the expected number (config["courts_per_slot"]).
    """
    total_penalty = 0
    for week in schedule:
        usage = {s: 0 for s in range(1, config["num_slots"]+1)}
        for level in week:
            slot_assignment, _, _ = week[level]
            for s in slot_assignment:
                usage[s] += 1
        for s, expected in config["courts_per_slot"].items():
            if usage[s] != expected:
                total_penalty += penalty_factor * abs(usage[s] - expected)
    return total_penalty

def objective(schedule, weight_play=0.1, weight_ref=10.0):
    """
    Overall objective: composite objective plus global slot usage penalty.
    """
    return composite_objective(schedule, weight_play, weight_ref) + compute_global_penalty(schedule)

def initialize_assignments(rr_pairings, mirror_mappings, total_weeks, max_attempts=100):
    """
    Try to randomly assign each mirror group a candidate slot/referee assignment
    until the reconstructed schedule satisfies the courts_per_slot constraint for every week.
    """
    for attempt in range(max_attempts):
        assignments = {}
        for level in levels:
            for r, weeks_list in mirror_mappings[level].items():
                pairing = rr_pairings[level][r]
                num_games = len(pairing)
                candidates = generate_level_slot_assignments(level, num_games)
                if not candidates:
                    # No candidate: use a dummy fallback.
                    assignments[(level, r)] = ((1,)*num_games, pairing, (0,)*num_games)
                    continue
                # Try a few times to get a valid referee assignment.
                valid_found = False
                for _ in range(20):
                    slot_assignment = random.choice(candidates)
                    ref_assignment = get_ref_assignment(level, slot_assignment, pairing, {t: 0 for t in teams[level]})
                    if ref_assignment is not None:
                        assignments[(level, r)] = (slot_assignment, pairing, ref_assignment)
                        valid_found = True
                        break
                if not valid_found:
                    assignments[(level, r)] = (candidates[0], pairing, (0,)*num_games)
        schedule = reconstruct_schedule(assignments, mirror_mappings, total_weeks, levels)
        if all(is_week_global_valid(week) for week in schedule):
            # Found a valid initial schedule.
            return assignments, schedule
    return None, None  # Failed to initialize a valid schedule

def generate_level_slot_assignments(level, num_games):
    """
    Generate candidate slot assignments for a level's round (num_games games).
    Each candidate is a tuple of length num_games with values in {1,...,config["num_slots"]}.
    
    Local constraints:
      - For each slot s, the number of games assigned to s is <= teams//3.
      - For rounds with 3 or more games, require at least 2 distinct slots and contiguous usage.
      - For rounds with fewer than 3 games, allow even a single slot.
    """
    assignments = []
    num_slots = config["num_slots"]
    num_teams = config["teams_per_level"][level]
    max_local = num_teams // 3  # Each game needs 2 teams playing + 1 team refereeing

    for candidate in product(range(1, num_slots + 1), repeat=num_games):
        slot_counts = {}
        for s in candidate:
            slot_counts[s] = slot_counts.get(s, 0) + 1

        # For rounds with 3 or more games, require at least 2 distinct slots.
        if num_games >= 3 and len(slot_counts) < 2:
            continue

        # Check that no slot exceeds max_local.
        if any(count > max_local for count in slot_counts.values()):
            continue

        # For rounds with 3 or more games, require contiguous slots.
        if num_games >= 3:
            min_slot = min(slot_counts.keys())
            max_slot = max(slot_counts.keys())
            if max_slot - min_slot + 1 != len(slot_counts):
                continue

        assignments.append(candidate)
    return assignments


def initialize_assignments(rr_pairings, mirror_mappings, total_weeks, max_attempts=100):
    """
    Try to randomly assign each mirror group a candidate slot/referee assignment
    until the reconstructed schedule satisfies the courts_per_slot constraint for every week.
    """
    for attempt in range(max_attempts):
        assignments = {}
        for level in levels:
            for r, weeks_list in mirror_mappings[level].items():
                pairing = rr_pairings[level][r]
                num_games = len(pairing)
                candidates = generate_level_slot_assignments(level, num_games)
                if not candidates:
                    assignments[(level, r)] = ((1,)*num_games, pairing, (0,)*num_games)
                    continue
                valid_found = False
                for _ in range(20):
                    slot_assignment = random.choice(candidates)
                    ref_assignment = get_ref_assignment(level, slot_assignment, pairing, {t: 0 for t in teams[level]})
                    if ref_assignment is not None:
                        assignments[(level, r)] = (slot_assignment, pairing, ref_assignment)
                        valid_found = True
                        break
                if not valid_found:
                    assignments[(level, r)] = (candidates[0], pairing, (0,)*num_games)
        schedule = reconstruct_schedule(assignments, mirror_mappings, total_weeks, levels)
        if all(is_week_global_valid(week) for week in schedule):
            return assignments, schedule
    return None, None  # Failed to initialize


def solve_game_schedule(rr_pairings, mirror_mappings, total_weeks, expected, max_restarts=100):
    """
    Backtracking solver that assigns each mirror group (i.e. each level's round) a candidate
    slot assignment (from generate_level_slot_assignments) so that, when aggregated, every week
    exactly meets the expected global slot distribution.
    
    Args:
      rr_pairings: dict mapping level -> list of rounds (base round-robin pairings)
      mirror_mappings: dict mapping level -> dict mapping round index -> list of week indices
      total_weeks: total number of weeks in the season
      expected: dict mapping slot -> expected count per week (e.g. {1:3, 2:2, 3:3})
      max_restarts: maximum number of random restarts before giving up
      
    Returns:
      assignments: dict mapping (level, round_index) -> candidate slot assignment (tuple)
                   or None if no assignment is found.
    """
    import random
    # Get all mirror groups as a list of keys.
    all_keys = []
    for level in rr_pairings:
        for r in mirror_mappings[level]:
            all_keys.append((level, r))
    
    def backtrack(i, assignments, week_totals, keys_order):
        if i == len(keys_order):
            # Check that every week meets the expected distribution.
            for w in range(total_weeks):
                if week_totals[w] != expected:
                    return False
            return True
        level, r = keys_order[i]
        pairing = rr_pairings[level][r]
        num_games = len(pairing)
        candidates = generate_level_slot_assignments(level, num_games)
        random.shuffle(candidates)
        for cand in candidates:
            # Compute candidate counts.
            local_counts = {}
            for s in cand:
                local_counts[s] = local_counts.get(s, 0) + 1
            valid = True
            for w in mirror_mappings[level][r]:
                for s, cnt in local_counts.items():
                    if week_totals[w][s] + cnt > expected[s]:
                        valid = False
                        break
                if not valid:
                    break
            if not valid:
                continue
            # Apply candidate: update week_totals.
            for w in mirror_mappings[level][r]:
                for s, cnt in local_counts.items():
                    week_totals[w][s] += cnt
            assignments[(level, r)] = cand
            if backtrack(i+1, assignments, week_totals, keys_order):
                return True
            # Backtrack: undo changes.
            for w in mirror_mappings[level][r]:
                for s, cnt in local_counts.items():
                    week_totals[w][s] -= cnt
            del assignments[(level, r)]
        return False

    for restart in range(max_restarts):
        # Shuffle the order of mirror groups.
        keys_order = all_keys[:]
        random.shuffle(keys_order)
        # Initialize week totals: for each week, for each slot in expected, count = 0.
        week_totals = {w: {s: 0 for s in expected} for w in range(total_weeks)}
        assignments = {}
        if backtrack(0, assignments, week_totals, keys_order):
            return assignments
    return None

def reconstruct_game_schedule(assignments, mirror_mappings, total_weeks):
    """
    Reconstruct full schedule (per week, per level) using the game slot assignments.
    The referee assignment is left blank (None) for now.
    """
    schedule = [{} for _ in range(total_weeks)]
    for level in levels:
        for r, weeks in mirror_mappings[level].items():
            cand = assignments[(level, r)]
            pairing = rr_pairings[level][r]
            for w in weeks:
                # For now store (slot_assignment, pairing, None)
                schedule[w][level] = (cand, pairing, None)
    return schedule

############################################
# Phase 2: Referee Assignment Optimization (SA)
############################################

def initialize_referee_assignments(schedule):
    new_schedule = copy.deepcopy(schedule)
    for w in range(len(new_schedule)):
        for level in new_schedule[w]:
            slot_assignment, pairing, ref_assignment = new_schedule[w][level]
            if ref_assignment is None:
                # Fallback: assign a default referee for each game
                ref_assignment = (0,) * len(pairing)
            new_schedule[w][level] = (slot_assignment, pairing, ref_assignment)
    return new_schedule


from itertools import product

def repair_final_ref_assignments(schedule, max_repair_iterations=1000):
    """
    Iteratively attempt to repair mirror groups that have a None referee assignment.
    For each mirror group with a None, try candidate moves (ref-only or combined) until a valid
    assignment is found. Returns a repaired schedule or None if repair fails.
    """
    new_schedule = copy.deepcopy(schedule)
    repair_iter = 0
    fixed = True
    while fixed and repair_iter < max_repair_iterations:
        fixed = False
        for level in levels:
            for r in mirror_mappings[level]:
                week_list = mirror_mappings[level][r]
                # Get the current assignment from the first week.
                s_assign, pairing, ref_assignment = new_schedule[week_list[0]][level]
                if ref_assignment is not None:
                    continue  # already valid
                # Try candidate moves for this mirror group:
                candidate_moves = []
                # Option 1: Ref-only moves (keep current slot assignment)
                candidate_lists = []
                for i in range(len(pairing)):
                    cands = candidate_referees_for_game(level, s_assign, pairing, i)
                    candidate_lists.append(cands)
                if all(candidate_lists):
                    for ref_candidate in product(*candidate_lists):
                        if len(set(ref_candidate)) == len(ref_candidate):
                            candidate_moves.append((s_assign, ref_candidate))
                # Option 2: Combined moves (change slot and ref assignment)
                for cand_slot in generate_level_slot_assignments(level, len(pairing)):
                    if cand_slot == s_assign:
                        continue
                    new_ref = get_ref_assignment(level, cand_slot, pairing, {t: 0 for t in teams[level]})
                    if new_ref is not None:
                        candidate_moves.append((cand_slot, new_ref))
                if candidate_moves:
                    new_slot, new_ref = random.choice(candidate_moves)
                    for w in week_list:
                        s_assgn, pairing_val, _ = new_schedule[w][level]
                        new_schedule[w][level] = (new_slot, pairing_val, new_ref)
                    fixed = True  # We fixed at least one mirror group this pass.
        repair_iter += 1
    # Final check:
    for week in new_schedule:
        for level in week:
            if week[level][2] is None:
                return None
    return new_schedule

def sa_referee_assignment(schedule, max_iterations=5000, initial_temp=100.0, cooling_rate=0.99):
    """
    Referee Assignment SA with Adjustment and Repair:
      - For a randomly chosen mirror group (identified by (level, r)), we try candidate moves
        that either update just the referee assignment (keeping the slot assignment fixed) or update both.
      - After applying the candidate move across all weeks in that mirror group, we rebuild the full schedule
        and hard-check that every week satisfies the courts_per_slot constraint.
      - At the end, if any mirror group still has no valid referee assignment, a repair routine is invoked.
    """
    current_schedule = copy.deepcopy(schedule)
    current_obj = referee_objective(current_schedule)
    temp = initial_temp

    # Build list of mirror group keys (each key is a tuple (level, r))
    mirror_keys = []
    for level in levels:
        for r in mirror_mappings[level]:
            mirror_keys.append((level, r))
    
    def get_representative(key):
        level, r = key
        week0 = mirror_mappings[level][r][0]
        return current_schedule[week0][level]  # (slot_assignment, pairing, ref_assignment)

    for iteration in range(max_iterations):
        # Select move type (here we use candidate moves and swaps; you can add repair moves if desired)
        key = random.choice(mirror_keys)
        level, r = key
        pairing = rr_pairings[level][r]
        num_games = len(pairing)
        week_list = mirror_mappings[level][r]
        rep_slot, _, current_ref_assignment = get_representative(key)

        candidate_moves = []
        # Option 1: Ref-only moves (keeping current slot assignment)
        candidate_lists = []
        for i in range(num_games):
            cands = candidate_referees_for_game(level, rep_slot, pairing, i)
            candidate_lists.append(cands)
        if all(candidate_lists):
            for ref_candidate in product(*candidate_lists):
                if len(set(ref_candidate)) == len(ref_candidate) and ref_candidate != current_ref_assignment:
                    candidate_moves.append((rep_slot, ref_candidate))
        # Option 2: Combined moves (change slot and ref assignment)
        for candidate_slot in generate_level_slot_assignments(level, num_games):
            if candidate_slot == rep_slot:
                continue
            new_ref = get_ref_assignment(level, candidate_slot, pairing, {t: 0 for t in teams[level]})
            if new_ref is not None:
                candidate_moves.append((candidate_slot, new_ref))
        if not candidate_moves:
            continue
        new_slot_assignment, new_ref_assignment = random.choice(candidate_moves)
        new_schedule = copy.deepcopy(current_schedule)
        for w in week_list:
            s_assign, pairing_val, _ = new_schedule[w][level]
            new_schedule[w][level] = (new_slot_assignment, pairing_val, new_ref_assignment)
        # Hard-check: global slot distribution must be maintained.
        if any(not is_week_global_valid(week) for week in new_schedule):
            continue
        new_obj = referee_objective(new_schedule)
        delta = new_obj - current_obj
        if delta < 0 or random.random() < math.exp(-delta / temp):
            current_schedule = new_schedule
            current_obj = new_obj
        temp *= cooling_rate

    # Final check: if any mirror group still has None, try a repair routine.
    repaired = repair_final_ref_assignments(current_schedule)
    if repaired is not None:
        current_schedule = repaired
    else:
        raise ValueError("After SA and repair, a game ended up with no valid referee assignment.")
    return current_schedule

def referee_objective(schedule):
    """
    Compute a global imbalance objective for referee assignments.
    Sums the variance of referee counts per level and adds huge penalties for any team
    whose total assignments fall outside [min_referee_count, max_referee_count].
    """
    overall = compute_overall_ref_counts(schedule)
    total = 0
    for level in levels:
        team_list = teams[level]
        values = [overall[level][t] for t in team_list]
        mean = sum(values) / len(values)
        total += sum((x - mean) ** 2 for x in values)
        for t in team_list:
            if overall[level][t] < config["min_referee_count"]:
                total += 1e6 * (config["min_referee_count"] - overall[level][t])
            if overall[level][t] > config["max_referee_count"]:
                total += 1e6 * (overall[level][t] - config["max_referee_count"])
    return total



# Example usage:
# full_schedule, assignments = solve_full_schedule_with_mirror_sa(rr_pairings, mirror_mappings, config["total_weeks"])
# is_valid, msg = validate_schedule(full_schedule, teams, levels)
# print("Final schedule valid:", is_valid, msg)

import copy

import copy

def fix_global_slot_distribution(schedule, expected):
    """
    Given a schedule (list of weeks, each a dict mapping level -> (slot_assignment, pairing, ref_assignment))
    and an expected slot distribution (e.g. {1: 3, 2: 2, 3: 3}), try to repair weeks whose
    distribution is off by adjusting one mirror group's candidate assignment.
    
    For each week with a mismatch, we iterate over levels (i.e. mirror groups) present in that week.
    For a given mirror group, we enumerate alternative candidate slot assignments (via generate_level_slot_assignments)
    and then for each candidate, we compute a new referee assignment via get_ref_assignment. If that candidate yields
    a simulated week distribution equal to the expected one, we update the mirror group (across all weeks) with the new candidate.
    
    This repair move uses get_ref_assignment so that the adjacent referee condition remains satisfied.
    """
    fixed_schedule = copy.deepcopy(schedule)
    num_weeks = len(fixed_schedule)
    
    for w_idx in range(num_weeks):
        week = fixed_schedule[w_idx]
        # Compute current distribution for this week.
        dist = {}
        for level in week:
            slot_assignment, _, _ = week[level]
            for s in slot_assignment:
                dist[s] = dist.get(s, 0) + 1
        
        if dist == expected:
            continue  # Week is fine.
        
        print(f"Week {w_idx+1} distribution is {dist}, expected {expected}. Attempting repair.")
        repaired = False
        
        # Try to adjust one mirror group in this week.
        for level in week:
            # Look up which mirror group (r_key) in this level covers this week.
            for r_key, weeks_list in mirror_mappings[level].items():
                if w_idx in weeks_list:
                    current_candidate, pairing, current_ref = fixed_schedule[w_idx][level]
                    # Enumerate alternative candidate slot assignments.
                    for cand in generate_level_slot_assignments(level, len(pairing)):
                        if cand == current_candidate:
                            continue
                        # Get a new referee assignment for this candidate.
                        new_ref = get_ref_assignment(level, cand, pairing, {t: 0 for t in teams[level]})
                        if new_ref is None:
                            continue
                        # Simulate the change: subtract counts of current candidate and add counts of new candidate.
                        simulated_dist = dist.copy()
                        for s in current_candidate:
                            simulated_dist[s] = simulated_dist.get(s, 0) - 1
                        for s in cand:
                            simulated_dist[s] = simulated_dist.get(s, 0) + 1
                        # Check if the simulated distribution matches the expected distribution.
                        if simulated_dist == expected:
                            print(f"  Level {level} mirror group {r_key}: changing {current_candidate} to {cand} with ref {new_ref} fixes week {w_idx+1}.")
                            # Update this mirror group in all weeks.
                            for w in weeks_list:
                                s_assign, pairing_val, _ = fixed_schedule[w][level]
                                fixed_schedule[w][level] = (cand, pairing_val, new_ref)
                            # Update our local distribution.
                            dist = simulated_dist
                            repaired = True
                            break
                    if repaired:
                        break
            if repaired:
                break
        if not repaired:
            print(f"  Could not repair week {w_idx+1}. Distribution remains {dist}.")
    return fixed_schedule



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
    violation_penalty = 1e6  # Penalty factor for exceeding the limit

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
            # If no referee assignment exists, skip this game (or use a fallback, e.g. (0,)*num_games)
            if ref_assignment is None:
                continue
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
        if usage[s] != config["courts_per_slot"].get(s, 0):
            return False
    return True


def composite_objective(schedule, weight_play=1.0, weight_ref=1.0):
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


def balance_schedule(schedule, mirror_mappings, max_iterations=300,
                     weight_play=0.1, weight_ref=10.0, cooling_rate=0.9,
                     initial_temp=5.0, candidate_prob=1.0, swap_prob=0.0):
    """
    Local search on a full schedule with mirror requirements.
    Candidate moves and swaps are applied per mirror group (i.e. a set of weeks sharing the same round).
    """
    new_schedule = copy.deepcopy(schedule)
    current_obj = composite_objective(new_schedule, weight_play, weight_ref)
    temperature = initial_temp

    for iteration in range(max_iterations):
        move_type = "candidate" if random.random() < candidate_prob else "swap"

        if move_type == "candidate":
            # Choose a random level and mirror group.
            level = random.choice(levels)
            mirror_groups = list(mirror_mappings[level].keys())
            if not mirror_groups:
                continue
            r = random.choice(mirror_groups)
            weeks_group = mirror_mappings[level][r]
            # Get current assignment from the first week in the group.
            week0 = weeks_group[0]
            current_assignment, pairing, current_ref = new_schedule[week0][level]
            # Generate alternative slot assignments for this mirror group.
            candidates = [a for a in generate_level_slot_assignments(level, len(pairing))
                          if a != current_assignment]
            if not candidates:
                continue
            new_assignment = random.choice(candidates)
            new_ref = get_ref_assignment(level, new_assignment, pairing, {t: 0 for t in teams[level]})
            if new_ref is None:
                continue

            # Backup current assignments and apply new one to all weeks in the group.
            backup = {}
            for w in weeks_group:
                backup[w] = new_schedule[w][level]
                new_schedule[w][level] = (new_assignment, pairing, new_ref)

            # Validate each affected week.
            if all(is_week_global_valid(new_schedule[w]) for w in weeks_group):
                candidate_obj = composite_objective(new_schedule, weight_play, weight_ref)
                delta = candidate_obj - current_obj
                if delta < 0 or random.random() < math.exp(-delta / temperature):
                    current_obj = candidate_obj
                    continue  # Accept the move.
            # Revert if move not accepted.
            for w in weeks_group:
                new_schedule[w][level] = backup[w]

        else:  # swap move
            # Swap two mirror groups in the same level.
            level = random.choice(levels)
            groups = list(mirror_mappings[level].keys())
            if len(groups) < 2:
                continue
            r1, r2 = random.sample(groups, 2)
            weeks1 = mirror_mappings[level][r1]
            weeks2 = mirror_mappings[level][r2]
            backup1 = {w: new_schedule[w][level] for w in weeks1}
            backup2 = {w: new_schedule[w][level] for w in weeks2}
            # Swap the assignments (all weeks in each group get the other's assignment).
            for w in weeks1:
                new_schedule[w][level] = backup2[weeks2[0]]
            for w in weeks2:
                new_schedule[w][level] = backup1[weeks1[0]]
            if all(is_week_global_valid(new_schedule[w]) for w in weeks1 + weeks2):
                candidate_obj = composite_objective(new_schedule, weight_play, weight_ref)
                delta = candidate_obj - current_obj
                if delta < 0 or random.random() < math.exp(-delta / temperature):
                    current_obj = candidate_obj
                    continue  # Accept the swap.
            # Revert swap if not accepted.
            for w in weeks1:
                new_schedule[w][level] = backup1[w]
            for w in weeks2:
                new_schedule[w][level] = backup2[w]

        if iteration % 10 == 0:
            temperature *= cooling_rate

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


#########################################
# Updated find_schedule_attempt
#########################################

#############################################
# 3. Update find_schedule_attempt to Use the New Solver
#############################################

def find_schedule_attempt():
    game_assignments = solve_game_schedule(rr_pairings, mirror_mappings, config["total_weeks"], expected=config["courts_per_slot"])
    if game_assignments is None:
        print("Failed to find a valid game schedule.")
        return None
    game_schedule = reconstruct_game_schedule(game_assignments, mirror_mappings, config["total_weeks"])
    # Phase 2: Assign referees with SA.
    full_schedule = sa_referee_assignment(game_schedule)
    full_schedule = fix_global_slot_distribution(full_schedule, expected=config["courts_per_slot"])
    return full_schedule
    # (Optionally, run the balance_schedule local search on full_schedule.)
    final_schedule = balance_schedule(full_schedule, mirror_mappings)
    is_valid, message = validate_schedule(final_schedule, teams, levels)
    print(message)
    if is_valid:
        return final_schedule
    return None




def find_schedule(
    use_saved_schedule=True,
    filename="saved_schedule.json",
    max_attempts=30000,
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
    # Validate configuration before proceeding
    validate_config(config)

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
    total_attempts = 0
    if num_cores == 1:
        # Sequential approach for single core
        for attempt in range(max_attempts):
            total_attempts += 1
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
                schedules = pool.starmap(
                    find_schedule_attempt, [()] * attempts_per_batch
                )
                for schedule in schedules:
                    if schedule is not None:
                        raw_schedule = schedule
                        break

            if raw_schedule is not None:
                break

            # Print progress every few batches
            if (attempt // attempts_per_batch) % 10 == 0:
                print(f"Attempted {attempt + attempts_per_batch} schedules...")
            total_attempts += attempts_per_batch

    if raw_schedule is None:
        print(f"\nNo valid schedule found after {max_attempts} attempts")
        return None, max_attempts

    # Format and save the successful schedule
    end_time = time.time()
    print(f"Schedule found in {end_time - start_time:.2f} seconds")

    # Convert to the standardized JSON format
    schedule_data = convert_to_formatted_schedule(raw_schedule, levels)

    # Save the newly generated schedule
    save_schedule_to_file(schedule_data, filename)
    print(f"Schedule saved to {filename}")

    return schedule_data, total_attempts


def validate_config(config):
    """
    Validate the configuration parameters before running the scheduling algorithm.
    Raises ValueError with detailed message if any constraint is violated.
    """
    # Calculate total teams and games per level
    total_teams = sum(config["teams_per_level"].values())
    total_games_per_round = total_teams // 2

    # 1. Check that sum of courts per slot equals total games per round
    courts_sum = sum(config["courts_per_slot"].values())
    if courts_sum != total_games_per_round:
        raise ValueError(
            f"Sum of courts per slot ({courts_sum}) must equal total games per round "
            f"(sum of teams per level / 2 = {total_games_per_round})"
        )

    # 2. Check that entries in courts_per_slot match num_slots
    if set(config["courts_per_slot"].keys()) != set(range(1, config["num_slots"] + 1)):
        raise ValueError(
            f"Keys in courts_per_slot must exactly match slots 1 through {config['num_slots']}"
        )

    # 3. Check that slot limits totals are sufficient
    games_per_team = (config["total_weeks"] * (total_teams - 1)) // total_teams
    slot_limits_sum = sum(config["slot_limits"].values())
    min_required = int(games_per_team * 1.5)
    if slot_limits_sum < min_required:
        raise ValueError(
            f"Sum of slot limits ({slot_limits_sum}) should be at least 1.5x the "
            f"number of games each team plays ({games_per_team}), which is {min_required}"
        )

    # 4. Check that priority slots count is reasonable
    if len(config["priority_slots"]) > 2:
        raise ValueError(
            f"Number of priority slots ({len(config['priority_slots'])}) should be 2 or fewer"
        )

    # Additional check: all priority slots should exist in the configuration
    for slot in config["priority_slots"]:
        if slot not in range(1, config["num_slots"] + 1):
            raise ValueError(
                f"Priority slot {slot} is outside the valid range (1-{config['num_slots']})"
            )

    return True


if __name__ == "__main__":
    from tests import (
        pairing_tests,
        cycle_pairing_test,
        global_slot_distribution_test,
        referee_player_test,
        adjacent_slot_test,
        mirror_pairing_test,
    )
    from stats import print_statistics

    filename = "/home/platelminto/Documents/dev/usbf-schedule/saved_schedule.json"

    # Validate configuration before running
    try:
        validate_config(config)
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)

    print("Generating new schedule...")
    start_time = time.time()
    final_schedule, total_attempts = find_schedule(use_saved_schedule=False)
    end_time = time.time()

    if final_schedule:
        print(f"Schedule found in {end_time - start_time:.2f} seconds")

    if final_schedule:
        print_schedule(final_schedule)
        print("\nRunning tests on final schedule:")
        pt = pairing_tests(final_schedule, levels, config["teams_per_level"])
        cpt = cycle_pairing_test(final_schedule, levels, config["teams_per_level"])
        rpt = referee_player_test(final_schedule)
        ast = adjacent_slot_test(final_schedule)
        gst = global_slot_distribution_test(final_schedule, config["courts_per_slot"])
        mpt = mirror_pairing_test(
            final_schedule, levels, config["teams_per_level"]
        )

        # Pass the config to print_statistics
        print_statistics(final_schedule, teams, levels, config)

        print("\nTest Results:")
        print(f"  Pairings correct: {pt}")
        print(f"  Cycle pairings: {cpt}")
        print(f"  No referee plays in their game: {rpt}")
        print(f"  Adjacent-slot condition: {ast}")
        print(f"  Global slot distribution: {gst}")
        print(f"  Mirror pairings: {mpt}")
    else:
        print("Failed to generate a valid schedule.")

    print(f"Total attempts: {total_attempts}")
