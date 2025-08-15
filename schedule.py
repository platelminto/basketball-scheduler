import pulp
import itertools
from collections import defaultdict

from tests import adjacent_slot_test, cycle_pairing_test, global_slot_distribution_test, pairing_tests, referee_player_test
from stats import print_statistics

def get_round_robin_length(num_teams):
    """Calculates the number of weeks for one full round-robin."""
    return num_teams - 1 if num_teams % 2 == 0 else num_teams

def phase_1_generate_multiple_matchups(config, team_names_by_level, num_blueprints_to_find=5):
    """
    Solves for weekly matchups multiple times, finding a different valid
    blueprint each time. This provides multiple starting points for Phase 2.
    """
    print(f"\n--- Starting Phase 1: Generating up to {num_blueprints_to_find} unique matchup blueprints ---")
    
    # --- Setup (Identical to the original Phase 1) ---
    total_weeks = config["total_weeks"]
    levels = config["levels"]
    all_teams = sorted([team for teams in team_names_by_level.values() for team in teams])
    team_to_level = {team: lvl for lvl, teams in team_names_by_level.items() for team in teams}
    weeks_range = range(total_weeks)
    
    all_possible_pairs = [tuple(sorted(p)) for lvl in levels for p in itertools.combinations(team_names_by_level[lvl], 2)]

    prob = pulp.LpProblem("MatchupScheduling_Multi", pulp.LpMinimize)
    plays_in_week = pulp.LpVariable.dicts("PlaysInWeek", (all_possible_pairs, weeks_range), cat='Binary')
    matchup_counts = pulp.LpVariable.dicts("MatchupCount", all_possible_pairs, cat='Integer')

    # --- Constraints (Identical to the original Phase 1) ---
    for level in levels:
        teams = team_names_by_level[level]
        num_teams = len(teams)
        if num_teams < 2: continue
        total_level_games = (num_teams * total_weeks) // 2
        level_pairs = [p for p in all_possible_pairs if p[0] in teams]
        min_plays = total_level_games // len(level_pairs)
        for pair in level_pairs:
            matchup_counts[pair].lowBound = min_plays
            matchup_counts[pair].upBound = min_plays + 1
            prob += pulp.lpSum(plays_in_week[pair][w] for w in weeks_range) == matchup_counts[pair]
        prob += pulp.lpSum(matchup_counts[pair] for pair in level_pairs) == total_level_games
    for team in all_teams:
        num_teams_in_level = len(team_names_by_level[team_to_level[team]])
        for w in weeks_range:
            games_in_week = pulp.lpSum(plays_in_week[p][w] for p in all_possible_pairs if team in p)
            if num_teams_in_level % 2 == 0: prob += games_in_week == 1
            else: prob += games_in_week <= 1
    for level in levels:
        teams = team_names_by_level[level]
        num_teams = len(teams)
        if num_teams < 2: continue
        rr_len = get_round_robin_length(num_teams)
        level_pairs = [p for p in all_possible_pairs if p[0] in teams]
        for pair in level_pairs:
            for w in range(total_weeks - rr_len):
                prob += plays_in_week[pair][w] == plays_in_week[pair][w + rr_len]

    # --- The "Find Multiple Solutions" Logic ---
    solver = pulp.PULP_CBC_CMD(msg=0)
    found_blueprints = []
    
    for i in range(num_blueprints_to_find):
        prob.solve(solver)
        
        if pulp.LpStatus[prob.status] == "Optimal":
            print(f"  Found blueprint #{i+1}...")
            # Store the found solution
            blueprint = []
            on_variables = []
            for w in weeks_range:
                games = []
                for pair in all_possible_pairs:
                    if plays_in_week[pair][w].varValue > 0.5:
                        games.append(pair)
                        on_variables.append(plays_in_week[pair][w])
                blueprint.append({'week': w, 'games': games})
            found_blueprints.append(blueprint)
            
            # Add a "no-good" cut: a constraint that forbids this exact solution from being found again.
            # It says "the sum of all variables that were 'on' in this solution must be less than the total number of them".
            prob += pulp.lpSum(on_variables) <= len(on_variables) - 1, f"No_Good_Cut_{i}"
        else:
            # If the solver can't find another optimal solution, we've found all possible blueprints.
            print(f"  No more unique blueprints found. Proceeding with {len(found_blueprints)} options.")
            break
            
    return found_blueprints

def phase_2_assign_slots_and_refs(config, team_names_by_level, weekly_matchups, time_limit: float, gapRel: float):
    """
    Takes a fixed weekly matchup schedule and assigns slots and referees.
    This phase contains the optimization objectives.
    NOW RETURNS the schedule AND its objective score.
    """
    # ... (The entire setup, variables, and constraints of Phase 2 are UNCHANGED) ...
    # --- Setup ---
    total_weeks = config["total_weeks"]
    num_slots = config["num_slots"]
    all_teams = sorted([team for teams in team_names_by_level.values() for team in teams])
    team_to_level = {team: lvl for lvl, teams in team_names_by_level.items() for team in teams}
    weeks_range = range(total_weeks)
    slots_range = range(1, num_slots + 1)
    all_games = [(g, w_data['week']) for w_data in weekly_matchups for g in w_data['games']]
    prob = pulp.LpProblem("SlotAndRefAssignment", pulp.LpMinimize)
    game_in_slot = pulp.LpVariable.dicts("GameInSlot", (all_games, slots_range), cat='Binary')
    refs = {}
    is_reffing = defaultdict(lambda: pulp.LpAffineExpression())
    for game, week in all_games:
        t1, t2 = game
        level = team_to_level[t1]
        possible_refs = [t for t in team_names_by_level[level] if t != t1 and t != t2]
        for t_ref in possible_refs:
            ref_vars = pulp.LpVariable.dicts(f"Ref_{t_ref}_{t1}_{t2}_{week}", slots_range, cat='Binary')
            refs[(t_ref, game, week)] = ref_vars
            for s in slots_range:
                is_reffing[(t_ref, week, s)] += ref_vars[s]
    is_playing = defaultdict(lambda: pulp.LpAffineExpression())
    for (t1, t2), w in all_games:
        for s in slots_range:
            var = game_in_slot[(t1, t2), w][s]
            is_playing[(t1, w, s)] += var
            is_playing[(t2, w, s)] += var
    for game, week in all_games:
        prob += pulp.lpSum(game_in_slot[game, week][s] for s in slots_range) == 1
    for w in weeks_range:
        games_this_week = [g for g, week in all_games if week == w]
        for s in slots_range:
            prob += pulp.lpSum(game_in_slot[g, w][s] for g in games_this_week) <= config["courts_per_slot"][s][w]
    for (t1, t2), w in all_games:
        level = team_to_level[t1]
        possible_refs = [t for t in team_names_by_level[level] if t != t1 and t != t2]
        for s in slots_range:
            prob += pulp.lpSum(refs[(tr, (t1,t2), w)][s] for tr in possible_refs) == game_in_slot[((t1,t2), w)][s]
    for t_ref in all_teams:
        for w in weeks_range:
            for s in slots_range:
                adjacent_play = pulp.LpAffineExpression()
                if s > 1: adjacent_play += is_playing[(t_ref, w, s - 1)]
                if s < num_slots: adjacent_play += is_playing[(t_ref, w, s + 1)]
                prob += is_reffing[(t_ref, w, s)] <= adjacent_play
    for t in all_teams:
        total_refs = pulp.lpSum(is_reffing[(t, w, s)] for w in weeks_range for s in slots_range)
        prob += total_refs >= config["min_referee_count"]
        prob += total_refs <= config["max_referee_count"]
        for s in slots_range:
            prob += pulp.lpSum(is_playing[(t, w, s)] for w in weeks_range) <= config["slot_limits"][s]
    # --- Objective Function (UNCHANGED) ---
    slot_imbalance_per_team = []
    for t in all_teams:
        plays_per_slot = {s: pulp.lpSum(is_playing[t,w,s] for w in weeks_range) for s in slots_range}
        min_games_in_slot = pulp.LpVariable(f"MinGamesInSlot_{t}", cat='Integer')
        max_games_in_slot = pulp.LpVariable(f"MaxGamesInSlot_{t}", cat='Integer')
        for s in slots_range:
            prob += plays_per_slot[s] >= min_games_in_slot
            prob += plays_per_slot[s] <= max_games_in_slot
        slot_imbalance_per_team.append(max_games_in_slot - min_games_in_slot)
    prob.setObjective(pulp.lpSum(slot_imbalance_per_team))

    # --- Solve ---
    solver = pulp.PULP_CBC_CMD(timeLimit=time_limit, gapRel=gapRel, msg=1) # msg=0 to keep the output clean
    prob.solve(solver)

    # --- Format Output ---
    if pulp.LpStatus[prob.status] in ["Optimal", "Feasible"]:
        objective_score = prob.objective.value() # Get the final score
        schedule_output = []
        for w in weeks_range:
            week_data = {"week": w + 1, "slots": {str(s): [] for s in slots_range}}
            games_this_week = [(g, wk) for g, wk in all_games if wk == w]
            for s in slots_range:
                for game, week in games_this_week:
                    if game_in_slot[(game, week)][s].varValue > 0.5:
                        t1, t2 = game
                        game_ref = "N/A"
                        level = team_to_level[t1]
                        possible_refs = [t for t in team_names_by_level[level] if t != t1 and t != t2]
                        for t_ref in possible_refs:
                            if refs[(t_ref, game, week)][s].varValue > 0.5:
                                game_ref = t_ref
                                break
                        week_data["slots"][str(s)].append({"level": level, "teams": [t1, t2], "ref": game_ref})
            schedule_output.append(week_data)
        return schedule_output, objective_score
    else:
        return None, None
        
def flip_teams_by_round(schedule, team_names_by_level):
    if not schedule: return schedule
    rr_lengths = {level: get_round_robin_length(len(teams)) for level, teams in team_names_by_level.items()}
    for week_data in schedule:
        week = week_data["week"] - 1
        for slot in week_data["slots"].values():
            for game in slot:
                level = game["level"]
                round_num = week // rr_lengths[level]
                if round_num % 2 == 1:
                    game["teams"] = [game["teams"][1], game["teams"][0]]
    return schedule

### NEW/MODIFIED ###
def generate_schedule(config, team_names_by_level, time_limit=60.0, num_blueprints_to_generate=6, gapRel=0.25):
    """
    Generates a schedule by first finding multiple unique matchup blueprints,
    then running a timed optimization on each one to find the best final schedule.
    """
    # Phase 1: Generate a list of potential blueprints
    blueprints = phase_1_generate_multiple_matchups(config, team_names_by_level, num_blueprints_to_generate)
    
    if not blueprints:
        print("\nScheduling failed in Phase 1. No valid matchup blueprints could be found.")
        return None
    
    # --- Phase 2: Evaluate each blueprint and find the best one ---
    print("\n--- Starting Phase 2: Evaluating all blueprints ---")
    
    best_schedule = None
    best_score = float('inf') # We want to minimize this score
    
    # Divide the total time limit among all the blueprints we need to test
    time_per_run = max(1.0, time_limit / len(blueprints)) # Ensure at least 1 second per run
    
    for i, blueprint in enumerate(blueprints):
        print(f"  Optimizing for Blueprint #{i+1}/{len(blueprints)} (time limit: {time_per_run:.1f}s)...")

        schedule, score = phase_2_assign_slots_and_refs(config, team_names_by_level, blueprint, time_limit=time_per_run, gapRel=gapRel)

        if schedule and score is not None:
            print(f"    -> Result: Feasible, Imbalance Score: {score}")
            if score < best_score:
                print(f"    -> NEW BEST FOUND!")
                best_score = score
                best_schedule = schedule
        else:
            print(f"    -> Result: Infeasible. This blueprint could not be scheduled.")
            
    if not best_schedule:
        print("\nScheduling failed in Phase 2. None of the blueprints resulted in a valid schedule.")
        return None
        
    print(f"\n--- Evaluation Complete. The best schedule found has an imbalance score of {best_score} ---")
    
    # Phase 3: Post-process the single best schedule found
    final_schedule = flip_teams_by_round(best_schedule, team_names_by_level)
        
    print("\nSuccessfully generated a complete schedule!")
    return final_schedule

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
        # "courts_per_slot": {
        #     1: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        #     2: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        #     3: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        #     4: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        # },
        "slot_limits": {1: 3, 2: 4, 3: 4, 4: 4},
        "min_referee_count": 4,
        "max_referee_count": 6,
    }
    TEAM_NAMES = {
        "A": [f"TeamA{i}" for i in range(1, CONFIG["teams_per_level"]["A"] + 1)],
        "B": [f"TeamB{i}" for i in range(1, CONFIG["teams_per_level"]["B"] + 1)],
        "C": [f"TeamC{i}" for i in range(1, CONFIG["teams_per_level"]["C"] + 1)],
    }
    
    ### NEW/MODIFIED ###
    # We now call the generator with a total time limit and the number of blueprints to try
    final_schedule = generate_schedule(CONFIG, TEAM_NAMES, time_limit=60, num_blueprints_to_generate=10, gapRel=0.25)

    if final_schedule:
        # These functions for testing and stats would be run as before
        run_comprehensive_tests(final_schedule, CONFIG, TEAM_NAMES)
        print_schedule_statistics(final_schedule, CONFIG, TEAM_NAMES)
