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


def compute_team_play_counts(schedule, teams, levels):
    """
    Compute how many times each team plays in each slot.

    Args:
        schedule: The formatted schedule data
        teams: List of team names or a number of teams or dict of teams by level
        levels: List of competition levels

    Returns:
        dict: Dictionary mapping levels to teams to slots to counts
    """
    # Create teams_dict based on the type of teams parameter
    teams_dict = create_teams_dict(teams, levels)

    # Initialize counts
    counts = {
        level: {t: {s: 0 for s in range(1, 5)} for t in teams_dict[level]}
        for level in levels
    }

    # Count team appearances in each slot
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in levels:
                    team1, team2 = game["teams"]
                    if team1 in teams_dict[level]:
                        counts[level][team1][slot] += 1
                    if team2 in teams_dict[level]:
                        counts[level][team2][slot] += 1

    return counts


def compute_team_ref_counts(schedule, teams, levels):
    """
    Compute how many times each team referees in each slot.

    Args:
        schedule: The formatted schedule data
        teams: List of team names or a number of teams or dict of teams by level
        levels: List of competition levels

    Returns:
        dict: Dictionary mapping levels to teams to slots to counts
    """
    # Create teams_dict based on the type of teams parameter
    teams_dict = create_teams_dict(teams, levels)

    # Initialize counts
    counts = {
        level: {t: {s: 0 for s in range(1, 5)} for t in teams_dict[level]}
        for level in levels
    }

    # Count referee assignments in each slot
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in levels:
                    referee = game["ref"]
                    if referee in teams_dict[level]:
                        counts[level][referee][slot] += 1

    return counts


def compute_overall_ref_counts(schedule, teams, levels):
    """
    Compute the total number of times each team referees.

    Args:
        schedule: The formatted schedule data
        teams: List of team names or a number of teams or dict of teams by level
        levels: List of competition levels

    Returns:
        dict: Dictionary mapping levels to teams to counts
    """
    # Create teams_dict based on the type of teams parameter
    teams_dict = create_teams_dict(teams, levels)

    # Initialize counts
    counts = {level: {t: 0 for t in teams_dict[level]} for level in levels}

    # Count total referee assignments
    for week in schedule:
        for slot_key, games in week["slots"].items():
            for game in games:
                level = game["level"]
                if level in levels:
                    referee = game["ref"]
                    if referee in teams_dict[level]:
                        counts[level][referee] += 1

    return counts


def create_teams_dict(teams, levels):
    """
    Create a dictionary of teams by level based on the input format.

    Args:
        teams: Can be:
               - int: number of teams per level
               - dict: already formatted as {level: [team names]}
               - list: list of team names to be extracted from the schedule
        levels: List of competition levels

    Returns:
        dict: Dictionary mapping levels to lists of team names
    """
    # If teams is an integer, create team names
    if isinstance(teams, int):
        teams_dict = {}
        for level in levels:
            if level == "A":
                teams_dict[level] = [f"HighTeam{i+1}" for i in range(teams)]
            elif level == "B":
                teams_dict[level] = [f"MidTeam{i+1}" for i in range(teams)]
            elif level == "C":
                teams_dict[level] = [f"LowTeam{i+1}" for i in range(teams)]
            else:
                teams_dict[level] = [f"{level}Team{i+1}" for i in range(teams)]
        return teams_dict

    # If teams is already a dictionary with the right structure, use it directly
    if isinstance(teams, dict) and all(level in teams for level in levels):
        return teams

    # If teams is a list or we need to extract team names from the schedule
    # For now, we'll just create default names
    teams_dict = {}
    for level in levels:
        if level == "A":
            teams_dict[level] = [f"HighTeam{i+1}" for i in range(6)]
        elif level == "B":
            teams_dict[level] = [f"MidTeam{i+1}" for i in range(6)]
        elif level == "C":
            teams_dict[level] = [f"LowTeam{i+1}" for i in range(6)]
        else:
            teams_dict[level] = [f"{level}Team{i+1}" for i in range(6)]

    return teams_dict


def print_statistics(schedule, teams, levels):
    """
    Print various statistics for the schedule.

    Args:
        schedule: The formatted schedule data
        teams: Number of teams per level, dict of team names, or list of teams
        levels: List of competition levels
    """
    print("\n=== STATISTICS ===")

    overall_ref = compute_overall_ref_counts(schedule, teams, levels)
    games_slot = compute_games_per_slot(schedule, levels)
    play_counts = compute_team_play_counts(schedule, teams, levels)
    team_ref = compute_team_ref_counts(schedule, teams, levels)

    print("\nGames per Level by Slot:")
    for level in games_slot:
        print(f"Level {level}:")
        for s in sorted(games_slot[level]):
            print(f"  Slot {s}: {games_slot[level][s]} games")

    print("\nTeam Play Counts (number of times a team plays in each slot):")
    for level in play_counts:
        print(f"Level {level}:")
        for team in sorted(play_counts[level].keys()):
            counts = play_counts[level][team]
            counts_str = ", ".join(f"Slot {s}: {counts[s]}" for s in sorted(counts))
            print(f"  {team}: {counts_str}")

    print("\nTeam Referee Counts (number of times a team referees, by slot):")
    for level in team_ref:
        print(f"Level {level}:")
        for team in sorted(team_ref[level].keys()):
            counts = team_ref[level][team]
            total = sum(counts.values())
            counts_str = ", ".join(f"Slot {s}: {counts[s]}" for s in sorted(counts))
            print(f"  {team}: {total} times ( {counts_str} )")

    print("\nBalance Statistics (Referee counts per team):")
    for level in overall_ref:
        vals = list(overall_ref[level].values())
        mean = sum(vals) / len(vals)
        variance = sum((x - mean) ** 2 for x in vals) / len(vals)
        stddev = math.sqrt(variance)
        print(f"Level {level}: Mean = {mean:.2f}, StdDev = {stddev:.2f}")
