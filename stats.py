import math


def compute_games_per_slot(schedule, teams_per_level):
    """
    Compute the number of games per slot for each level.

    Args:
        schedule: The formatted schedule data
        teams_per_level: Dictionary mapping levels to team names

    Returns:
        dict: Dictionary mapping levels to slots to game counts
    """
    # Get num_slots from schedule structure
    num_slots = len(schedule[0]["slots"]) if schedule else 4
    
    counts = {level: {s: 0 for s in range(1, num_slots + 1)} for level in teams_per_level.keys()}

    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in teams_per_level:
                    counts[level][slot] += 1

    return counts


def create_teams_dict(teams_per_level):
    """
    Create a standardized teams dictionary with name-to-index mappings.
    """
    name_to_index = {}
    index_to_name = {}

    for level, team_names in teams_per_level.items():
        name_to_index[level] = {}
        index_to_name[level] = {}

        for idx, name in enumerate(team_names):
            name_to_index[level][name] = idx
            index_to_name[level][idx] = name

    return {
        "name_to_index": name_to_index,
        "index_to_name": index_to_name,
    }


def compute_team_play_counts(schedule, teams_per_level):
    """
    Compute how many times each team plays in each slot.
    """
    # Create teams dictionary with mappings
    teams_data = create_teams_dict(teams_per_level)
    name_to_index = teams_data["name_to_index"]
    
    # Get num_slots from schedule structure
    num_slots = len(schedule[0]["slots"]) if schedule else 4
    
    # Initialize counts
    counts = {
        level: {
            idx: {s: 0 for s in range(1, num_slots + 1)}
            for idx in range(len(team_names))
        }
        for level, team_names in teams_per_level.items()
    }

    # Count team appearances in each slot
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in teams_per_level:
                    for team_name in game["teams"]:
                        if team_name in name_to_index[level]:
                            team_idx = name_to_index[level][team_name]
                            counts[level][team_idx][slot] += 1

    return counts


def compute_team_ref_counts(schedule, team_names_by_level):
    """
    Compute how many times each team referees in each slot.
    """
    # Create teams dictionary with mappings
    teams_data = create_teams_dict(team_names_by_level)
    name_to_index = teams_data["name_to_index"]
    
    # Get num_slots from schedule structure
    num_slots = len(schedule[0]["slots"]) if schedule else 4
    
    # Initialize counts
    counts = {
        level: {
            idx: {s: 0 for s in range(1, num_slots + 1)}
            for idx in range(len(team_names))
        }
        for level, team_names in team_names_by_level.items()
    }

    # Count referee assignments in each slot
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in team_names_by_level:
                    ref_name = game["ref"]
                    if ref_name in name_to_index[level]:
                        ref_idx = name_to_index[level][ref_name]
                        counts[level][ref_idx][slot] += 1

    return counts


def compute_overall_ref_counts(schedule, team_names_by_level):
    """
    Compute total times each team referees across all slots.
    """
    # Create teams dictionary with mappings
    teams_data = create_teams_dict(team_names_by_level)
    name_to_index = teams_data["name_to_index"]

    counts = {
        level: {idx: 0 for idx in range(len(team_names))}
        for level, team_names in team_names_by_level.items()
    }

    for week in schedule:
        for _, games in week["slots"].items():
            for game in games:
                level = game["level"]
                if level in team_names_by_level:
                    ref_name = game["ref"]
                    if ref_name in name_to_index[level]:
                        ref_idx = name_to_index[level][ref_name]
                        counts[level][ref_idx] += 1

    return counts


def print_statistics(schedule, team_names_by_level):
    """
    Print various statistics for the schedule.
    """

    print("\n=== STATISTICS ===")

    # Create teams dictionary with mappings
    teams_data = create_teams_dict(team_names_by_level)
    index_to_name = teams_data["index_to_name"]
    
    # Get num_slots from schedule structure
    num_slots = len(schedule[0]["slots"]) if schedule else 4

    overall_ref = compute_overall_ref_counts(schedule, team_names_by_level)
    games_slot = compute_games_per_slot(schedule, team_names_by_level)
    play_counts = compute_team_play_counts(schedule, team_names_by_level)
    team_ref = compute_team_ref_counts(schedule, team_names_by_level)

    # Print games per slot with breakdown by level
    print("\nGames per Slot:")
    for slot in range(1, num_slots + 1):
        print(f"  Slot {slot}:")
        for level in team_names_by_level.keys():
            level_games = games_slot[level][slot] if slot in games_slot[level] else 0
            print(f"    Level {level}: {level_games} games")
        # Total for this slot
        total_games = sum(
            games_slot[level][slot] if slot in games_slot[level] else 0
            for level in team_names_by_level.keys()
        )
        print(f"    Total: {total_games} games")

    # Print combined play counts for all teams in all levels in one section
    print("\nTeam Play Counts:")
    for i, level in enumerate(team_names_by_level.keys()):
        # Print a dividing line before each level (except the first)
        if i > 0:
            print("  " + "-" * 40)  # 40-character dividing line

        # Print level header
        print(f"  Level {level}:")

        for team_idx in sorted(play_counts[level].keys()):
            team_name = index_to_name[level][team_idx]

            # Create a compact representation of slot play counts
            slot_counts = []
            for slot in range(1, num_slots + 1):
                plays = play_counts[level][team_idx][slot]
                refs = team_ref[level][team_idx][slot]
                slot_counts.append(f"Slot {slot}: {plays} (refs {refs})")

            slot_str = ", ".join(slot_counts)
            print(f"    {team_name}: {slot_str}")

    # Print referee totals as a separate section at the bottom
    print("\nReferee Totals:")
    for level in team_names_by_level.keys():
        print(f"  Level {level}:")
        for team_idx in sorted(overall_ref[level].keys()):
            team_name = index_to_name[level][team_idx]
            count = overall_ref[level][team_idx]
            print(f"    {team_name}: {count} times")
