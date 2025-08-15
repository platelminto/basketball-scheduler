import math


def compute_games_per_slot(schedule, levels):
    """
    Compute the number of games per slot for each level.

    Args:
        schedule: The formatted schedule data
        levels: List of competition levels (e.g., ["A", "B", "C"])

    Returns:
        dict: Dictionary mapping levels to slots to game counts
    """
    counts = {level: {s: 0 for s in range(1, 5)} for level in levels}

    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in levels:
                    counts[level][slot] += 1

    return counts


def create_teams_dict(teams, levels, config=None):
    """
    Create a standardized teams dictionary based on the type of input.
    Makes the function work with either team indices or team names.
    """
    # Use global config if not provided
    if config is None:
        from schedule_old import config

    teams_dict = {}

    # Handle different input types
    if isinstance(teams, dict):
        # Teams is already a dict mapping levels to teams
        teams_dict = teams
    elif isinstance(teams, int):
        # Teams is a number - create numbered teams for each level
        teams_dict = {level: list(range(teams)) for level in levels}
    else:
        # Teams is a list - split evenly across levels
        teams_per_level = len(teams) // len(levels)
        for i, level in enumerate(levels):
            start = i * teams_per_level
            end = start + teams_per_level
            teams_dict[level] = teams[start:end]

    # Create a mapping between team names and indices
    name_to_index = {}
    index_to_name = {}

    for level in levels:
        team_count = config["teams_per_level"][level]
        name_to_index[level] = {}
        index_to_name[level] = {}

        # Create the mappings based on level
        for idx in range(team_count):
            # Use team names from config instead of hardcoded names
            if level in config["team_names_by_level"] and idx < len(
                config["team_names_by_level"][level]
            ):
                name = config["team_names_by_level"][level][idx]
            else:
                # Fallback to old naming pattern if config is incomplete
                if level == "A":
                    name = f"HighTeam{idx+1}"
                elif level == "B":
                    name = f"MidTeam{idx+1}"
                elif level == "C":
                    name = f"LowTeam{idx+1}"
                else:
                    name = f"{level}Team{idx+1}"

            name_to_index[level][name] = idx
            index_to_name[level][idx] = name

    return {
        "by_index": teams_dict,
        "name_to_index": name_to_index,
        "index_to_name": index_to_name,
    }


def compute_team_play_counts(schedule, teams, levels, config=None):
    """
    Compute how many times each team plays in each slot.
    Works with both team indices and team names.
    """
    # Use global config if not provided
    if config is None:
        from schedule_old import config

    # Create teams dictionary with mappings
    teams_data = create_teams_dict(teams, levels, config)
    teams_dict = teams_data["by_index"]
    name_to_index = teams_data["name_to_index"]

    # Initialize counts - use configurable number of slots
    counts = {
        level: {
            t: {s: 0 for s in range(1, config["num_slots"] + 1)}
            for t in teams_dict[level]
        }
        for level in levels
    }

    # Count team appearances in each slot
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in levels:
                    for team_name in game["teams"]:
                        # Convert team name to index for counting
                        if team_name in name_to_index[level]:
                            team_idx = name_to_index[level][team_name]
                            if team_idx in teams_dict[level]:
                                counts[level][team_idx][slot] += 1

    return counts


def compute_team_ref_counts(schedule, teams, levels, config=None):
    """
    Compute how many times each team referees in each slot.
    Works with both team indices and team names.
    """
    # Use global config if not provided
    if config is None:
        from schedule_old import config

    # Create teams dictionary with mappings
    teams_data = create_teams_dict(teams, levels, config)
    teams_dict = teams_data["by_index"]
    name_to_index = teams_data["name_to_index"]

    # Initialize counts - use configurable number of slots
    counts = {
        level: {
            t: {s: 0 for s in range(1, config["num_slots"] + 1)}
            for t in teams_dict[level]
        }
        for level in levels
    }

    # Count referee assignments in each slot
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in levels:
                    ref_name = game["ref"]
                    if ref_name in name_to_index[level]:
                        ref_idx = name_to_index[level][ref_name]
                        if ref_idx in teams_dict[level]:
                            counts[level][ref_idx][slot] += 1

    return counts


def compute_overall_ref_counts(schedule, teams, levels, config=None):
    """
    Compute total times each team referees across all slots.
    Works with both team indices and team names.
    """
    # Use global config if not provided
    if config is None:
        from schedule_old import config

    # Create teams dictionary with mappings
    teams_data = create_teams_dict(teams, levels, config)
    teams_dict = teams_data["by_index"]
    name_to_index = teams_data["name_to_index"]

    counts = {level: {t: 0 for t in teams_dict[level]} for level in levels}

    for week in schedule:
        for _, games in week["slots"].items():
            for game in games:
                level = game["level"]
                if level in levels:
                    ref_name = game["ref"]
                    if ref_name in name_to_index[level]:
                        ref_idx = name_to_index[level][ref_name]
                        if ref_idx in teams_dict[level]:
                            counts[level][ref_idx] += 1

    return counts


def print_statistics(schedule, teams, levels, config):
    """
    Print various statistics for the schedule.
    Works with both team indices and team names.
    Compact view with all teams together.
    """

    print("\n=== STATISTICS ===")

    # Create teams dictionary with mappings
    teams_data = create_teams_dict(teams, levels, config)
    index_to_name = teams_data["index_to_name"]

    overall_ref = compute_overall_ref_counts(schedule, teams, levels, config)
    games_slot = compute_games_per_slot(schedule, levels)
    play_counts = compute_team_play_counts(schedule, teams, levels, config)
    team_ref = compute_team_ref_counts(schedule, teams, levels, config)

    # Print games per slot with breakdown by level
    print("\nGames per Slot:")
    for slot in range(1, config["num_slots"] + 1):
        print(f"  Slot {slot}:")
        for level in levels:
            level_games = games_slot[level][slot] if slot in games_slot[level] else 0
            print(f"    Level {level}: {level_games} games")
        # Total for this slot
        total_games = sum(
            games_slot[level][slot] if slot in games_slot[level] else 0
            for level in levels
        )
        print(f"    Total: {total_games} games")

    # Print combined play counts for all teams in all levels in one section
    print("\nTeam Play Counts:")
    for i, level in enumerate(levels):
        # Print a dividing line before each level (except the first)
        if i > 0:
            print("  " + "-" * 40)  # 40-character dividing line

        # Print level header
        print(f"  Level {level}:")

        for team_idx in sorted(play_counts[level].keys()):
            team_name = index_to_name[level][team_idx]

            # Create a compact representation of slot play counts
            slot_counts = []
            for slot in range(1, config["num_slots"] + 1):
                plays = play_counts[level][team_idx][slot]
                refs = team_ref[level][team_idx][slot]
                slot_counts.append(f"Slot {slot}: {plays} (refs {refs})")

            slot_str = ", ".join(slot_counts)
            print(f"    {team_name}: {slot_str}")

    # Print referee totals as a separate section at the bottom
    print("\nReferee Totals:")
    for level in levels:
        print(f"  Level {level}:")
        for team_idx in sorted(overall_ref[level].keys()):
            team_name = index_to_name[level][team_idx]
            count = overall_ref[level][team_idx]
            print(f"    {team_name}: {count} times")
