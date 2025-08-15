import pulp
import itertools
from collections import defaultdict

from tests import adjacent_slot_test, cycle_pairing_test, global_slot_distribution_test, pairing_tests, referee_player_test
from stats import print_statistics

def get_round_robin_length(num_teams):
    """Calculates the number of weeks for one full round-robin."""
    return num_teams - 1 if num_teams % 2 == 0 else num_teams

def phase_1_generate_matchups(config, team_names_by_level):
    """
    Solves for the weekly matchups only, ignoring slots and referees.
    This is a feasibility problem and should be very fast.
    """
    print("\n--- Starting Phase 1: Generating Weekly Matchups ---")
    
    # --- Setup ---
    total_weeks = config["total_weeks"]
    levels = config["levels"]
    all_teams = sorted([team for teams in team_names_by_level.values() for team in teams])
    team_to_level = {team: lvl for lvl, teams in team_names_by_level.items() for team in teams}
    weeks_range = range(total_weeks)
    
    all_possible_pairs = [tuple(sorted(p)) for lvl in levels for p in itertools.combinations(team_names_by_level[lvl], 2)]

    prob = pulp.LpProblem("MatchupScheduling", pulp.LpMinimize)

    # --- Decision Variables ---
    plays_in_week = pulp.LpVariable.dicts("PlaysInWeek", (all_possible_pairs, weeks_range), cat='Binary')
    matchup_counts = pulp.LpVariable.dicts("MatchupCount", all_possible_pairs, cat='Integer')

    # --- Constraints ---
    # Flexible matchup counts
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
            prob += pulp.lpSum(plays_in_week[pair][w] for w in weeks_range) == matchup_counts[pair], f"Link_Count_{pair[0]}_{pair[1]}"
        
        prob += pulp.lpSum(matchup_counts[pair] for pair in level_pairs) == total_level_games, f"Total_Games_{level}"

    # Strengthened Weekly Play constraint
    for team in all_teams:
        num_teams_in_level = len(team_names_by_level[team_to_level[team]])
        for w in weeks_range:
            games_in_week = pulp.lpSum(plays_in_week[p][w] for p in all_possible_pairs if team in p)
            if num_teams_in_level % 2 == 0:
                prob += games_in_week == 1, f"Weekly_Play_Exact_{team}_{w}"
            else:
                prob += games_in_week <= 1, f"Weekly_Play_Max_{team}_{w}"

    # Cyclical Pairing constraint
    for level in levels:
        teams = team_names_by_level[level]
        num_teams = len(teams)
        if num_teams < 2: continue
        rr_len = get_round_robin_length(num_teams)
        level_pairs = [p for p in all_possible_pairs if p[0] in teams]
        for pair in level_pairs:
            for w in range(total_weeks - rr_len):
                prob += plays_in_week[pair][w] == plays_in_week[pair][w + rr_len], f"Cycle_Pairing_{pair[0]}_{pair[1]}_{w}"

    # --- Solve ---
    solver = pulp.PULP_CBC_CMD(msg=0)
    prob.solve(solver)

    if pulp.LpStatus[prob.status] == "Optimal":
        print("Phase 1 Successful: Found a valid matchup schedule.")
        weekly_matchups = []
        for w in weeks_range:
            games = [pair for pair in all_possible_pairs if plays_in_week[pair][w].varValue > 0.5]
            weekly_matchups.append({'week': w, 'games': games})
        return weekly_matchups
    else:
        print(f"Phase 1 FAILED: Could not find a valid matchup schedule. Status: {pulp.LpStatus[prob.status]}")
        return None

def phase_2_assign_slots_and_refs(config, team_names_by_level, weekly_matchups, time_limit: float):
    """
    Takes a fixed weekly matchup schedule and assigns slots and referees.
    This phase contains the optimization objectives.
    """
    print("\n--- Starting Phase 2: Assigning Slots and Referees ---")

    # --- Setup ---
    total_weeks = config["total_weeks"]
    num_slots = config["num_slots"]
    all_teams = sorted([team for teams in team_names_by_level.values() for team in teams])
    team_to_level = {team: lvl for lvl, teams in team_names_by_level.items() for team in teams}
    weeks_range = range(total_weeks)
    slots_range = range(1, num_slots + 1)
    
    # Create a flat list of all games to be scheduled
    all_games = [(g, w_data['week']) for w_data in weekly_matchups for g in w_data['games']]

    prob = pulp.LpProblem("SlotAndRefAssignment", pulp.LpMinimize)

    # --- Decision Variables ---
    game_in_slot = pulp.LpVariable.dicts("GameInSlot", (all_games, slots_range), cat='Binary')
    
    # Define refs only for valid assignments (team reffing a game in its own level)
    # and build the is_reffing helper at the same time.
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

    # --- Helper Expressions ---
    is_playing = defaultdict(lambda: pulp.LpAffineExpression())
    for (t1, t2), w in all_games:
        for s in slots_range:
            var = game_in_slot[(t1, t2), w][s]
            is_playing[(t1, w, s)] += var
            is_playing[(t2, w, s)] += var

    # --- Constraints ---
    # Each game must be assigned to exactly one slot
    for game, week in all_games:
        prob += pulp.lpSum(game_in_slot[game, week][s] for s in slots_range) == 1, f"Assign_Game_{game[0]}_{game[1]}_{week}"
    
    # Court Capacity
    for w in weeks_range:
        games_this_week = [g for g, week in all_games if week == w]
        for s in slots_range:
            prob += pulp.lpSum(game_in_slot[g, w][s] for g in games_this_week) <= config["courts_per_slot"][s][w], f"Court_Capacity_{w}_{s}"

    # Referee Assignment (one ref per game)
    for (t1, t2), w in all_games:
        level = team_to_level[t1]
        possible_refs = [t for t in team_names_by_level[level] if t != t1 and t != t2]
        for s in slots_range:
            # A ref must be assigned if the game is in this slot
            prob += pulp.lpSum(refs[(tr, (t1,t2), w)][s] for tr in possible_refs) == game_in_slot[((t1,t2), w)][s], f"Assign_Ref_{t1}_{t2}_{w}_{s}"

    # Referee Adjacency (a team can only ref if playing adjacently)
    for t_ref in all_teams:
        for w in weeks_range:
            for s in slots_range:
                adjacent_play = pulp.LpAffineExpression()
                if s > 1: adjacent_play += is_playing[(t_ref, w, s - 1)]
                if s < num_slots: adjacent_play += is_playing[(t_ref, w, s + 1)]
                
                # The number of games a team refs in a slot (0 or 1) must be <= their adjacent play status (0, 1, or 2)
                prob += is_reffing[(t_ref, w, s)] <= adjacent_play, f"Ref_Adjacency_{t_ref}_{w}_{s}"

    # Season Slot & Referee Limits
    for t in all_teams:
        # CORRECT: Use the is_reffing helper which is correctly scoped to same-level reffing.
        total_refs = pulp.lpSum(is_reffing[(t, w, s)] for w in weeks_range for s in slots_range)
        prob += total_refs >= config["min_referee_count"], f"Min_Ref_Count_{t}"
        prob += total_refs <= config["max_referee_count"], f"Max_Ref_Count_{t}"
        for s in slots_range:
            prob += pulp.lpSum(is_playing[(t, w, s)] for w in weeks_range) <= config["slot_limits"][s], f"Slot_Limit_{t}_{s}"

    # --- Objective Function ---    
    # This will hold the slot count imbalance for each team
    slot_imbalance_per_team = []
    
    for t in all_teams:
        # Get the raw count of games played by team 't' in each slot
        plays_per_slot = {s: pulp.lpSum(is_playing[t,w,s] for w in weeks_range) for s in slots_range}
        
        # CRITICAL: Define Min/Max variables as Integers to represent the game counts
        min_games_in_slot = pulp.LpVariable(f"MinGamesInSlot_{t}", cat='Integer')
        max_games_in_slot = pulp.LpVariable(f"MaxGamesInSlot_{t}", cat='Integer')
        
        for s in slots_range:
            # Force the min/max variables to bound the actual game counts
            prob += plays_per_slot[s] >= min_games_in_slot
            prob += plays_per_slot[s] <= max_games_in_slot
        
        # The imbalance for this team is the integer range of their slot counts
        slot_imbalance_per_team.append(max_games_in_slot - min_games_in_slot)

    # The final objective is to minimize the SUM of all teams' integer imbalances.
    # This provides a strong, realistic bound for the solver.
    prob.setObjective(pulp.lpSum(slot_imbalance_per_team))

    # --- Solve ---
    solver = pulp.PULP_CBC_CMD(timeLimit=time_limit, msg=1)
    prob.solve(solver)

    # --- Format Output ---
    if pulp.LpStatus[prob.status] in ["Optimal", "Feasible"]:
        print(f"Phase 2 Successful! Status: {pulp.LpStatus[prob.status]}")
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
                            # --- THIS IS THE CORRECTED LINE ---
                            # Access refs with the tuple key: (t_ref, game, week)
                            if refs[(t_ref, game, week)][s].varValue > 0.5:
                                game_ref = t_ref
                                break
                        week_data["slots"][str(s)].append({"level": level, "teams": [t1, t2], "ref": game_ref})
            schedule_output.append(week_data)
        return schedule_output
    else:
        print(f"Phase 2 FAILED: Could not assign slots/refs. Status: {pulp.LpStatus[prob.status]}")
        return None

def flip_teams_by_round(schedule, team_names_by_level):
    """
    Post-processing to flip team order in every round per level.
    For each level, calculate its round robin length and flip teams in odd rounds.
    """
    if not schedule:
        return schedule
    
    # Calculate round robin length for each level
    rr_lengths = {}
    for level, teams in team_names_by_level.items():
        rr_lengths[level] = get_round_robin_length(len(teams))
    
    for week_data in schedule:
        week = week_data["week"] - 1  # Convert to 0-indexed
        
        for slot in week_data["slots"].values():
            for game in slot:
                level = game["level"]
                rr_len = rr_lengths[level]
                round_num = week // rr_len  # Which round we're in (0, 1, 2, ...)
                
                # If it's an odd round (1, 3, 5, ...), flip the teams
                if round_num % 2 == 1:
                    game["teams"] = [game["teams"][1], game["teams"][0]]
    
    return schedule

def generate_schedule(config, team_names_by_level, time_limit=5.0):
    """
    Generates a schedule using a two-phase optimization approach.
    Phase 1: Determine weekly matchups.
    Phase 2: Assign slots and referees to those matchups.
    Phase 3: Post-process to flip team order by round per level.
    """
    # Phase 1: Get the abstract weekly matchup schedule
    weekly_matchups = phase_1_generate_matchups(config, team_names_by_level)
    
    if not weekly_matchups:
        print("\nScheduling failed in Phase 1. No solution possible.")
        return None
        
    # Phase 2: Assign slots and refs to the generated matchups
    final_schedule = phase_2_assign_slots_and_refs(config, team_names_by_level, weekly_matchups, time_limit=time_limit)

    if not final_schedule:
        print("\nScheduling failed in Phase 2.")
        return None
    
    # Phase 3: Flip team order for alternating rounds per level
    final_schedule = flip_teams_by_round(final_schedule, team_names_by_level)
        
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
        # "courts_per_slot": {  # for 4 games
        #     1: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        #     2: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        #     3: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        #     4: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
        # },
        "slot_limits": {1: 3, 2: 5, 3: 5, 4: 4},
        "min_referee_count": 4,
        "max_referee_count": 6,
    }
    TEAM_NAMES = {
        "A": [f"TeamA{i}" for i in range(1, CONFIG["teams_per_level"]["A"] + 1)],
        "B": [f"TeamB{i}" for i in range(1, CONFIG["teams_per_level"]["B"] + 1)],
        "C": [f"TeamC{i}" for i in range(1, CONFIG["teams_per_level"]["C"] + 1)],
    }
    final_schedule = generate_schedule(CONFIG, TEAM_NAMES, 5) # , optimize_for_balance=True, gapRel=0.2)

    if final_schedule:
        run_comprehensive_tests(final_schedule, CONFIG, TEAM_NAMES)
        print_schedule_statistics(final_schedule, CONFIG, TEAM_NAMES)

    # print(final_schedule)