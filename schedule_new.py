import pulp
import itertools
from collections import defaultdict

from tests import adjacent_slot_test, cycle_pairing_test, global_slot_distribution_test, pairing_tests, referee_player_test
from stats import print_statistics

def get_round_robin_length(num_teams):
    """Calculates the number of weeks for one full round-robin."""
    if num_teams % 2 == 0:
        return num_teams - 1
    else:
        return num_teams

def generate_schedule(config, team_names_by_level, optimize_for_balance=True):
    """
    Generates a league schedule using an MIP model.

    This version includes multiple advanced optimizations:
    - Cyclical Pairing Constraint: Enforces matchup repetition.
    - Strengthened Weekly Play: Enforces teams in even-sized levels play exactly once per week.
    - Symmetry Breaking: Adds a constraint to prune redundant solutions.
    """
    print("Starting schedule generation...")
    print(">> RUNNING WITH ADVANCED OPTIMIZATIONS ENABLED <<")

    # 1. Pre-computation and Setup
    print("Step 1: Pre-computing parameters...")
    levels = config["levels"]
    total_weeks = config["total_weeks"]
    num_slots = config["num_slots"]

    all_teams = sorted([team for level_teams in team_names_by_level.values() for team in level_teams])
    team_to_level = {team: level for level, level_teams in team_names_by_level.items() for team in level_teams}
    
    weeks_range = range(total_weeks)
    slots_range = range(1, num_slots + 1)
    
    # This dictionary will now only contain all possible pairs, not a pre-calculated count.
    all_possible_pairs = []
    for level in levels:
        teams_in_level = team_names_by_level[level]
        if len(teams_in_level) < 2: continue
        all_possible_pairs.extend(list(itertools.combinations(teams_in_level, 2)))
    
    # Sort pairs for deterministic behavior
    all_possible_pairs = [tuple(sorted(p)) for p in all_possible_pairs]

    # 2. Initialize the MIP Model
    print("Step 2: Initializing the MIP model...")
    prob = pulp.LpProblem("LeagueScheduling_Optimized", pulp.LpMinimize)

    # 3. Define Decision Variables
    print("Step 3: Defining decision variables...")
    match_keys = all_possible_pairs
    matches = pulp.LpVariable.dicts("Match", (match_keys, weeks_range, slots_range), cat='Binary')
    refs = pulp.LpVariable.dicts("Ref", (all_teams, match_keys, weeks_range, slots_range), cat='Binary')

    is_playing = defaultdict(lambda: pulp.LpAffineExpression())
    for t1, t2 in match_keys:
        for w in weeks_range:
            for s in slots_range:
                match_var = matches[t1, t2][w][s]
                is_playing[(t1, w, s)] += match_var
                is_playing[(t2, w, s)] += match_var

    is_reffing = defaultdict(lambda: pulp.LpAffineExpression())
    for t_ref in all_teams:
        for t1, t2 in match_keys:
            if team_to_level[t_ref] == team_to_level[t1]:
                for w in weeks_range:
                    for s in slots_range:
                        is_reffing[(t_ref, w, s)] += refs[t_ref][t1, t2][w][s]

    # 4. Add Constraints
    print("Step 4: Adding constraints to the model...")
    
        # --- NEW: FLEXIBLE MATCHUP COUNT CONSTRAINTS ---
    print("Step 4a: Defining flexible matchup count variables...")
    
    matchup_counts = pulp.LpVariable.dicts("MatchupCount", match_keys, cat='Integer')

    for level in levels:
        teams_in_level = team_names_by_level[level]
        num_teams = len(teams_in_level)
        if num_teams < 2: continue
        
        total_games_per_team = total_weeks
        total_level_games = (num_teams * total_games_per_team) // 2
        
        level_pairs = [p for p in match_keys if p[0] in teams_in_level]
        num_pairs = len(level_pairs)

        # Calculate the lower and upper bounds for how many times a pair can play
        min_plays = total_level_games // num_pairs
        max_plays = min_plays + 1

        for pair in level_pairs:
            # Constrain the count for each pair
            matchup_counts[pair].lowBound = min_plays
            matchup_counts[pair].upBound = max_plays

            # Link this count to the actual match variables
            prob += pulp.lpSum(matches[pair][w][s] for w in weeks_range for s in slots_range) == matchup_counts[pair], f"Link_Match_Count_{pair[0]}_{pair[1]}"

        # Ensure the sum of counts for the level is correct
        prob += pulp.lpSum(matchup_counts[pair] for pair in level_pairs) == total_level_games, f"Total_Level_Games_{level}"
    
    # Strengthener 1: Total Games Constraint
    for t in all_teams:
        prob += pulp.lpSum(is_playing[(t, w, s)] for w in weeks_range for s in slots_range) == total_weeks, f"Total_Games_{t}"

    # Hard Constraint: Cyclical Pairing
    for level in levels:
        teams_in_level = team_names_by_level[level]
        num_teams = len(teams_in_level)
        if num_teams < 2: continue
        rr_len = get_round_robin_length(num_teams)
        level_pairs = list(itertools.combinations(teams_in_level, 2))
        for t1, t2 in level_pairs:
            pair = tuple(sorted((t1, t2)))
            for w in range(total_weeks - rr_len):
                match_in_w = pulp.lpSum(matches[pair][w][s] for s in slots_range)
                match_in_w_cycle = pulp.lpSum(matches[pair][w + rr_len][s] for s in slots_range)
                prob += match_in_w == match_in_w_cycle, f"Cycle_Pairing_{t1}_{t2}_{w}"

    # --- STRATEGY 1: STRENGTHENED WEEKLY PLAY CONSTRAINT ---
    print("Step 4a: Adding Strengthened Weekly Play constraint...")
    for t in all_teams:
        level = team_to_level[t]
        num_teams_in_level = len(team_names_by_level[level])
        for w in weeks_range:
            # If the number of teams in the level is even, a team MUST play every week.
            # If odd, they must play AT MOST once (allowing for a bye week).
            if num_teams_in_level % 2 == 0:
                prob += pulp.lpSum(is_playing[(t, w, s)] for s in slots_range) == 1, f"Weekly_Play_Exact_{t}_{w}"
            else:
                prob += pulp.lpSum(is_playing[(t, w, s)] for s in slots_range) <= 1, f"Weekly_Play_Max_{t}_{w}"
    
    # --- STRATEGY 2: SYMMETRY BREAKING CONSTRAINT ---
    print("Step 4b: Adding Symmetry Breaking constraint...")
    # Find the first available game slot in the entire season
    first_w, first_s = -1, -1
    for w_search in weeks_range:
        for s_search in slots_range:
            if config["courts_per_slot"][s_search][w_search] > 0:
                first_w, first_s = w_search, s_search
                break
        if first_w != -1:
            break
    
    # If a valid slot exists, force the alphabetically first team to play in it.
    # This prevents the solver from exploring identical schedules where team roles are swapped.
    if first_w != -1:
        first_team_in_league = all_teams[0]
        prob += is_playing[(first_team_in_league, first_w, first_s)] == 1, f"Symmetry_Break_{first_team_in_league}"

    # C3: Court Capacity
    for w in weeks_range:
        for s in slots_range:
            prob += pulp.lpSum(matches[t1, t2][w][s] for t1, t2 in match_keys) <= config["courts_per_slot"][s][w], f"Court_Capacity_{w}_{s}"
            
    # Other core constraints... (C4, C5, C6, C7)
    # (These are unchanged from the previous version)
    for (t1, t2) in match_keys:
        for w in weeks_range:
            for s in slots_range:
                level = team_to_level[t1]
                possible_refs = [t for t in team_names_by_level[level] if t != t1 and t != t2]
                prob += pulp.lpSum(refs[t_ref][t1, t2][w][s] for t_ref in possible_refs) == matches[t1, t2][w][s], f"Ref_Assignment_{t1}_{t2}_{w}_{s}"
    for t_ref in all_teams:
        for w in weeks_range:
            for s in slots_range:
                adjacent_play = pulp.LpAffineExpression()
                if s > 1: adjacent_play += is_playing[(t_ref, w, s - 1)]
                if s < num_slots: adjacent_play += is_playing[(t_ref, w, s + 1)]
                prob += is_reffing[(t_ref, w, s)] <= adjacent_play, f"Ref_Adjacency_{t_ref}_{w}_{s}"
    for t in all_teams:
        for s in slots_range:
            prob += pulp.lpSum(is_playing[(t, w, s)] for w in weeks_range) <= config["slot_limits"][s], f"Slot_Limit_{t}_{s}"
    for t in all_teams:
        total_refs = pulp.lpSum(is_reffing[(t, w, s)] for w in weeks_range for s in slots_range)
        prob += total_refs >= config["min_referee_count"], f"Min_Ref_Count_{t}"
        prob += total_refs <= config["max_referee_count"], f"Max_Ref_Count_{t}"

    # 5. Define the Objective Function (Conditional)
    print("Step 5: Handling objective function...")
    if optimize_for_balance:
        # ... (Objective function code remains the same as the previous version) ...
        print(">> Optimization is ENABLED. Building balancing objective.")
        total_refs_per_team = {t: pulp.lpSum(is_reffing[(t, w, s)] for w in weeks_range for s in slots_range) for t in all_teams}
        min_total_refs = pulp.LpVariable("MinTotalRefs", lowBound=0, cat='Integer')
        max_total_refs = pulp.LpVariable("MaxTotalRefs", lowBound=0, cat='Integer')
        for t in all_teams:
            prob += total_refs_per_team[t] >= min_total_refs
            prob += total_refs_per_team[t] <= max_total_refs
        ref_imbalance = max_total_refs - min_total_refs
        total_slot_games = defaultdict(int)
        for s in slots_range:
            total_slot_games[s] = sum(config["courts_per_slot"][s])
        slot_imbalances = []
        for t in all_teams:
            normalized_plays = []
            for s in slots_range:
                if total_slot_games[s] > 0:
                    normalized_plays.append(pulp.lpSum(is_playing[(t, w, s)] for w in weeks_range) / total_slot_games[s])
            if len(normalized_plays) > 1:
                min_norm_play = pulp.LpVariable(f"MinNormPlay_{t}", lowBound=0, upBound=1)
                max_norm_play = pulp.LpVariable(f"MaxNormPlay_{t}", lowBound=0, upBound=1)
                for i, np in enumerate(normalized_plays):
                    prob += np >= min_norm_play
                    prob += np <= max_norm_play
                slot_imbalances.append(max_norm_play - min_norm_play)
        total_slot_imbalance = pulp.lpSum(slot_imbalances)
        prob.setObjective(ref_imbalance + total_slot_imbalance)
    else:
        print(">> Optimization is DISABLED. Solving for feasibility only.")
        pass

    # 6. Solve the Problem
    print("Step 6: Solving the model...")
    solver = pulp.PULP_CBC_CMD(timeLimit=300, msg=1) 
    prob.solve(solver)
    
    # 7. Post-processing and Output Formatting
    # (This section is unchanged)
    print("Step 7: Formatting the output...")
    if pulp.LpStatus[prob.status] in ["Optimal", "Feasible"]:
        print(f"Solution Found! Status: {pulp.LpStatus[prob.status]}")
        schedule_output = []
        for w in weeks_range:
            week_data = {"week": w + 1, "slots": {str(s): [] for s in slots_range}}
            for s in slots_range:
                for (t1, t2) in match_keys:
                    if matches[t1, t2][w][s].varValue > 0.5:
                        game_ref = "N/A"
                        level = team_to_level[t1]
                        possible_refs = [t for t in team_names_by_level[level] if t not in [t1, t2]]
                        for t_ref in possible_refs:
                            if refs[t_ref][t1, t2][w][s].varValue > 0.5:
                                game_ref = t_ref
                                break
                        game_entry = { "level": level, "teams": [t1, t2], "ref": game_ref }
                        week_data["slots"][str(s)].append(game_entry)
            schedule_output.append(week_data)
        return schedule_output
    else:
        print(f"Could not find a solution. Status: {pulp.LpStatus[prob.status]}")
        return None

# The main execution block and validation function remain the same.
# Just use them as they were in the previous version.
if __name__ == '__main__':
    # ... your CONFIG and TEAM_NAMES dictionaries ...
    # ... your validation function ...
    # ... call generate_schedule(...) ...
    pass

def run_comprehensive_tests(schedule, config, team_names_by_level):
    """Run all tests from tests.py on the generated schedule."""
    if not schedule:
        print("No schedule to test.")
        return
    
    print("\n=== COMPREHENSIVE SCHEDULE TESTING ===")
    
    # Extract parameters from config
    levels = config["levels"]
    teams_per_level = config["teams_per_level"]
    expected_courts_per_slot = config["courts_per_slot"]
    num_slots = config["num_slots"]
    
    all_passed = True
    
    # Run each test
    tests_to_run = [
        ("Pairing Tests", lambda: pairing_tests(schedule, levels, teams_per_level)),
        ("Global Slot Distribution", lambda: global_slot_distribution_test(schedule, expected_courts_per_slot, num_slots)),
        ("Referee Player Conflict", lambda: referee_player_test(schedule)),
        ("Adjacent Slot Referee", lambda: adjacent_slot_test(schedule)),
        # ("Mirror Pairing", lambda: mirror_pairing_test(schedule, first_half_weeks)),
        ("Cycle Pairing", lambda: cycle_pairing_test(schedule, levels, teams_per_level))
    ]
    
    for test_name, test_func in tests_to_run:
        print(f"\n--- {test_name} ---")
        try:
            passed, errors = test_func()
            if not passed:
                all_passed = False
                print(f"❌ {test_name} FAILED")
                for error in errors:
                    print(f"   {error}")
            else:
                print(f"✅ {test_name} PASSED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            all_passed = False
    
    print(f"\n=== OVERALL RESULT: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'} ===")
    return all_passed

def print_schedule_statistics(schedule, config, team_names_by_level):
    """Print detailed statistics about the generated schedule."""
    if not schedule:
        print("No schedule to analyze.")
        return
    
    # Adapt config format for stats.py functions
    stats_config = config.copy()
    stats_config["team_names_by_level"] = team_names_by_level
    
    # Use the levels from config
    levels = config["levels"]
    
    # Create team indices mapping for stats.py (it expects integer team indices)
    teams_as_indices = {}
    for level in levels:
        teams_as_indices[level] = list(range(len(team_names_by_level[level])))
    
    # Print statistics using stats.py
    print_statistics(schedule, teams_as_indices, levels, stats_config)

if __name__ == "__main__":
    CONFIG = {
        "levels": ["A", "B", "C"],
        "teams_per_level": {"A": 6, "B": 6, "C": 6},
        "total_weeks": 10,
        "num_slots": 4,
        "courts_per_slot": {
            1: [1, 1, 2, 2, 2, 2, 2, 2, 2, 2],
            2: [3, 3, 2, 2, 2, 2, 2, 2, 2, 2],
            3: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            4: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        },
        # "courts_per_slot": {  # for 4 games
        #     1: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        #     2: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        #     3: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        #     4: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        # },
        "slot_limits": {1: 4, 2: 6, 3: 6, 4: 4},
        "min_referee_count": 3,
        "max_referee_count": 7,
    }
    TEAM_NAMES = {
        "A": [f"TeamA{i}" for i in range(1, CONFIG["teams_per_level"]["A"] + 1)],
        "B": [f"TeamB{i}" for i in range(1, CONFIG["teams_per_level"]["B"] + 1)],
        "C": [f"TeamC{i}" for i in range(1, CONFIG["teams_per_level"]["C"] + 1)],
    }
    final_schedule = generate_schedule(CONFIG, TEAM_NAMES, False)

    if final_schedule:
        run_comprehensive_tests(final_schedule, CONFIG, TEAM_NAMES)
        print_schedule_statistics(final_schedule, CONFIG, TEAM_NAMES)

    # print(final_schedule)