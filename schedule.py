import random
from itertools import product, permutations
import math
import copy
from multiprocessing import Pool

###########################
# Parameters & Round-Robin
###########################

teams = list(range(6))  # Teams 0..5 (displayed as 1..6)
levels = ["A", "B", "C"]
first_half_weeks = 5  # Weeks 1–5; second half will mirror these for weeks 6–10
total_weeks = 10

# The three available slot distributions.
# (When one level gets (1,2,2), another (2,3,4) and the third (3,4,4),
# the overall weekly capacities are met:
#  Slot 1: 1 game, Slot 2: 3 games, Slot 3: 2 games, Slot 4: 3 games.)
distributions_list = [
    (1, 2, 2),  # low-slot distribution
    (2, 3, 4),  # middle distribution
    (3, 4, 4),  # high-slot distribution
]


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
    rr_pairings[level] = generate_round_robin_pairings(6)  # 5 rounds for 6 teams

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
    for t in range(6):
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
        ref_counts = {level: {t: 0 for t in teams} for level in levels}
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
    Compute a weighted global imbalance metric based solely on hard limits.
    For each level and team for each slot:
      - Slot 1 has a hard limit of 2.
      - Slot 4 has a hard limit of 4.
      - Slots 2 and 3 have a hard limit of 6.
    If the actual count exceeds the limit, add:
         violation_penalty * (count - limit)^2.
    For slots 1 and 4, multiply the penalty by an extra multiplier.
    Lower values indicate better balance.
    """
    play_counts = compute_team_play_counts(schedule)  # level -> {team -> {slot: count}}
    total = 0.0
    violation_penalty = 1e7  # Penalty factor for exceeding the limit
    extra_multiplier = 100  # Extra multiplier for slots 1 and 4

    for level in levels:
        for t in teams:
            for s in [1, 2, 3, 4]:
                count = play_counts[level][t][s]
                # Set limits per slot.
                if s == 1:
                    limit = 2
                elif s == 4:
                    limit = 4
                else:  # slots 2 and 3
                    limit = 6
                if count > limit:
                    if s in [1, 4]:
                        total += (
                            violation_penalty * extra_multiplier * (count - limit) ** 2
                        )
                    else:
                        total += violation_penalty * (count - limit) ** 2
    return total


def balance_playing_slots(schedule, max_iter=10000, initial_temp=1.0, cooling_rate=0.01):
    """
    Combined simulated annealing move operator with a richer move set.
    
    In each iteration, we randomly choose among four moves:
      - Block Move: Reassign a contiguous block of weeks with new random permutations.
      - Swap Move: For a randomly chosen level, swap its entire assignment between two weeks.
      - Rotation Move: For a randomly chosen level in one week, rotate its distribution tuple.
      - Individual-Level Reassignment: For one level in one week, reassign a new random distribution.
      
    For each affected week (and its mirror) the round-robin pairing is fixed and a valid
    referee assignment is recomputed (using dummy ref counts so that only eligibility is enforced).
    
    After the candidate move, we check that the set of distributions across levels in each affected week
    equals set(distributions_list). The move is accepted based on the weighted play imbalance metric.
    """
    new_schedule = copy.deepcopy(schedule)
    current_cost = weighted_play_imbalance_metric(new_schedule)
    temp = initial_temp
    first_half = first_half_weeks  # number of weeks in first half

    def week_distribution_ok(week):
        dists = set(week[level][0] for level in week)
        return dists == set(distributions_list)

    for it in range(max_iter):
        candidate_schedule = copy.deepcopy(new_schedule)
        affected_weeks = set()
        move_type_rand = random.random()
        
        # We'll assign equal probability to each move type.
        if move_type_rand < 0.25:
            # Swap Move: Pick one level and two distinct weeks in first half, then swap that level's assignment.
            level = random.choice(levels)
            week1, week2 = random.sample(range(first_half), 2)
            candidate_schedule[week1][level], candidate_schedule[week2][level] = (
                candidate_schedule[week2][level],
                candidate_schedule[week1][level],
            )
            affected_weeks.update([week1, week2, week1 + first_half, week2 + first_half])
        elif move_type_rand < 0.5:
            # Block Move: Change a block of weeks.
            possible_block_sizes = [bs for bs in [2, 3, 5] if bs <= first_half]
            block_size = random.choice(possible_block_sizes)
            start_w = random.randrange(0, first_half - block_size + 1)
            for w in range(start_w, start_w + block_size):
                candidate_perm = random.choice(list(permutations(distributions_list)))
                for level in levels:
                    pairing = candidate_schedule[w][level][1]  # fixed pairing
                    new_dist = candidate_perm[levels.index(level)]
                    candidate_ref = get_ref_assignment(new_dist, pairing, {t: 0 for t in teams})
                    if candidate_ref is None:
                        candidate_schedule = None
                        break
                    candidate_schedule[w][level] = (new_dist, pairing, candidate_ref)
                    affected_weeks.add(w)
                    mirror_w = w + first_half
                    if mirror_w < len(candidate_schedule):
                        candidate_schedule[mirror_w][level] = (new_dist, pairing, candidate_ref)
                        affected_weeks.add(mirror_w)
                if candidate_schedule is None:
                    break
            if candidate_schedule is None:
                continue
        elif move_type_rand < 1:
            # Rotation Move: For one level in one week, rotate its distribution.
            level = random.choice(levels)
            w = random.choice(range(first_half))
            distribution, pairing, ref_assignment = candidate_schedule[w][level]
            # Choose a rotation: there are 3 possible non-trivial rotations of a 3-tuple.
            # For example, if distribution = (a,b,c), possible rotations: (b,c,a) or (c,a,b).
            rot = random.choice([1, 2])
            new_distribution = distribution[rot:] + distribution[:rot]
            candidate_ref = get_ref_assignment(new_distribution, pairing, {t: 0 for t in teams})
            if candidate_ref is None:
                continue
            candidate_schedule[w][level] = (new_distribution, pairing, candidate_ref)
            mirror_w = w + first_half
            if mirror_w < len(candidate_schedule):
                candidate_schedule[mirror_w][level] = (new_distribution, pairing, candidate_ref)
            affected_weeks.update([w, mirror_w])
        
        # Check that every affected week maintains the correct overall slot distribution.
        valid_move = True
        for w in affected_weeks:
            if w < len(candidate_schedule) and not week_distribution_ok(candidate_schedule[w]):
                valid_move = False
                break
        if not valid_move:
            continue
        
        candidate_cost = weighted_play_imbalance_metric(candidate_schedule)
        delta = candidate_cost - current_cost
        if delta < 0 or random.random() < math.exp(-delta / temp):
            new_schedule = candidate_schedule
            current_cost = candidate_cost
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
        level: {t: {s: 0 for s in [1, 2, 3, 4]} for t in teams} for level in levels
    }
    for week in schedule:
        for level in week:
            distribution, pairing, _ = week[level]
            for i in range(3):
                slot = distribution[i]
                t1, t2 = pairing[i]
                counts[level][t1][slot] += 1
                counts[level][t2][slot] += 1
    return counts


##############################################
# Phase 2: Referee Post-Processing
##############################################


def compute_overall_ref_counts(schedule):
    counts = {level: {t: 0 for t in teams} for level in levels}
    for week in schedule:
        for level in week:
            _, _, ref_assignment = week[level]
            for r in ref_assignment:
                counts[level][r] += 1
    return counts


#####################################
# Local Moves for Referee Balancing (Swapping Games)
#####################################


def move_ref_games_schedule(schedule, max_iterations=1000):
    """
    Attempt to improve referee balance by swapping the pairings between two games within
    a level (and recomputing referee assignments) in a given week, without altering the fixed
    slot distribution. Any change is mirrored to the corresponding second-half week.

    Before accepting a candidate move, we check that the set of slot distributions for that week
    (and its mirror) remains exactly equal to set(distributions_list). This ensures that the global
    slot distribution (e.g. Slot1:1, Slot2:3, Slot3:2, Slot4:3) is preserved.
    """
    new_schedule = copy.deepcopy(schedule)

    def imbalance(level, overall_counts):
        vals = list(overall_counts[level].values())
        mean = sum(vals) / len(vals)
        return sum(abs(x - mean) for x in vals)

    def week_distribution_ok(week):
        # For a given week (a dict mapping level->(distribution, pairing, ref_assignment)),
        # check that the set of distributions equals the required set.
        dists = set(week[level][0] for level in week)
        return dists == set(distributions_list)

    overall = compute_overall_ref_counts(new_schedule)
    current_balance = {level: imbalance(level, overall) for level in levels}

    improved = True
    iteration = 0
    while improved and iteration < max_iterations:
        improved = False
        overall = compute_overall_ref_counts(new_schedule)
        for w in range(first_half_weeks):
            # Check that the week and its mirror currently have the right distributions.
            if not week_distribution_ok(new_schedule[w]):
                print(f"Week {w+1} distribution check failed before move!")
                continue
            mirror_w = w + first_half_weeks
            if mirror_w < len(new_schedule) and not week_distribution_ok(
                new_schedule[mirror_w]
            ):
                print(
                    f"Mirror week {mirror_w+1} distribution check failed before move!"
                )
                continue
            for level in levels:
                distribution, pairing, ref_assignment = new_schedule[w][level]
                best_assignment = (distribution, pairing, ref_assignment)
                best_balance = current_balance[level]
                # Try swapping pairings between two games (indices 0,1), (0,2), or (1,2).
                for i, j in [(0, 1), (0, 2), (1, 2)]:
                    new_pairing = pairing.copy()
                    new_pairing[i], new_pairing[j] = new_pairing[j], new_pairing[i]
                    # The distribution remains unchanged.
                    new_ref_assignment = get_ref_assignment(
                        distribution, new_pairing, overall[level]
                    )
                    if new_ref_assignment is None:
                        continue
                    candidate = (distribution, new_pairing, new_ref_assignment)
                    # Ensure the distribution portion is identical.
                    if candidate[0] != distribution:
                        continue  # must not change distribution
                    # Also, verify that this candidate move does not change the week's overall distributions.
                    # (Since we haven't changed distribution for any level in this week, this should be OK.)
                    # Now estimate new overall ref counts for this level if we accept the move.
                    temp_counts = overall[level].copy()
                    for t in ref_assignment:
                        temp_counts[t] -= 1
                    for t in new_ref_assignment:
                        temp_counts[t] += 1
                    new_balance = sum(
                        abs(x - (sum(temp_counts.values()) / 6))
                        for x in temp_counts.values()
                    )
                    if new_balance < best_balance:
                        best_balance = new_balance
                        best_assignment = candidate
                # If an improved assignment was found, tentatively update the week.
                if best_assignment != (distribution, pairing, ref_assignment):
                    # Temporarily update week w for this level.
                    original = new_schedule[w][level]
                    new_schedule[w][level] = best_assignment
                    # Mirror the change in the corresponding second-half week.
                    if mirror_w < len(new_schedule):
                        original_mirror = new_schedule[mirror_w][level]
                        new_schedule[mirror_w][level] = best_assignment
                    # Check that both week and mirror still have the required distributions.
                    if not week_distribution_ok(new_schedule[w]) or (
                        mirror_w < len(new_schedule)
                        and not week_distribution_ok(new_schedule[mirror_w])
                    ):
                        # Revert the change.
                        new_schedule[w][level] = original
                        if mirror_w < len(new_schedule):
                            new_schedule[mirror_w][level] = original_mirror
                    else:
                        overall = compute_overall_ref_counts(new_schedule)
                        current_balance[level] = imbalance(level, overall)
                        improved = True
        iteration += 1
    return new_schedule


#########################################
# Run Post-Processing Phases & Testing
#########################################


def validate_schedule(schedule, teams, levels):
    """
    Validate that:
    1. No team referees more than 6 times in any level
    2. No team plays more than 2 times in slot 1 in any level
    3. No team plays more than 5 times in slot 4 in any level
    Returns (bool, str) - (is_valid, error_message)
    """
    # Check referee counts
    ref_counts = {level: {t: 0 for t in teams} for level in levels}
    for week in schedule:
        for level in week:
            _, _, ref_assignment = week[level]
            for r in ref_assignment:
                ref_counts[level][r] += 1

    for level in levels:
        for team in teams:
            if ref_counts[level][team] > 6:
                return (
                    False,
                    f"Team {team+1} referees {ref_counts[level][team]} times in level {level}",
                )

    # Check slot 1 and slot 4 play counts
    play_counts = {level: {t: {1: 0, 4: 0} for t in teams} for level in levels}
    for week in schedule:
        for level in week:
            distribution, pairing, _ = week[level]
            for i, slot in enumerate(distribution):
                if slot in [1, 4]:
                    t1, t2 = pairing[i]
                    play_counts[level][t1][slot] += 1
                    play_counts[level][t2][slot] += 1

    for level in levels:
        for team in teams:
            if play_counts[level][team][1] > 2:
                return (
                    False,
                    f"Team {team+1} plays {play_counts[level][team][1]} times in slot 1 in level {level}",
                )
            if play_counts[level][team][4] > 4:
                return (
                    False,
                    f"Team {team+1} plays {play_counts[level][team][4]} times in slot 4 in level {level}",
                )

    return True, "Schedule is valid"


def print_schedule(schedule):
    """
    Print schedule week by week, slot by slot.
    Teams are displayed as A1-A6, B1-B6, C1-C6.
    """

    def team_name(team, level):
        return f"{level}{team + 1}"

    print("\n=== FULL SCHEDULE ===")
    for week_num, week in enumerate(schedule, 1):
        print(f"\nWEEK {week_num}")
        print("-" * 50)

        # Collect all games for each slot
        slot_games = {1: [], 2: [], 3: [], 4: []}
        for level in levels:
            distribution, pairing, ref_assignment = week[level]
            for game_idx, (slot, pair, ref) in enumerate(
                zip(distribution, pairing, ref_assignment)
            ):
                team1, team2 = pair
                slot_games[slot].append(
                    {
                        "level": level,
                        "teams": (team_name(team1, level), team_name(team2, level)),
                        "ref": team_name(ref, level),
                    }
                )

        # Print games slot by slot
        for slot in range(1, 5):
            if slot_games[slot]:
                print(f"\nSlot {slot}:")
                for game in slot_games[slot]:
                    print(
                        f"  {game['level']}: {game['teams'][0]} vs {game['teams'][1]} (Ref: {game['ref']})"
                    )


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


def find_schedule(max_attempts=10000, num_cores=16):
    """
    Try to find a valid schedule using parallel processing.
    Uses num_cores processes, making max_attempts total tries.
    """
    print(f"Searching for valid schedule using {num_cores} cores...")
    attempts_per_batch = num_cores
    for attempt in range(0, max_attempts, attempts_per_batch):
        with Pool(num_cores) as pool:
            schedules = pool.starmap(find_schedule_attempt, [()] * attempts_per_batch)
            for schedule in schedules:
                if schedule is not None:
                    return schedule

    print(f"\nNo valid schedule found after {max_attempts} attempts")
    return None


if __name__ == "__main__":
    from tests import (
        pairing_tests,
        global_slot_distribution_test,
        referee_player_test,
        adjacent_slot_test,
    )
    from stats import print_statistics

    final_schedule = find_schedule()

    if final_schedule is not None:
        print_schedule(final_schedule)
        print("\nRunning tests on final schedule:")
        pt = pairing_tests(final_schedule, levels, teams)
        rpt = referee_player_test(final_schedule)
        ast = adjacent_slot_test(final_schedule)
        gst = global_slot_distribution_test(final_schedule)
        print("\nTest Results:")
        print(f"  Pairings correct: {pt}")
        print(f"  No referee plays in their game: {rpt}")
        print(f"  Adjacent-slot condition: {ast}")
        print(f"  Global slot distribution: {gst}")
        print_statistics(final_schedule, teams, levels)
    else:
        print("No valid schedule generated.")
