def pairing_tests(schedule, levels, teams_per_level):
    """
    Tests that each team pair plays the correct number of times during the season.
    When levels have different team counts, pairings may occur more than twice.

    Args:
        schedule: The formatted schedule data
        levels: List of competition levels (e.g., ["A", "B", "C"])
        teams_per_level: Dict mapping each level to its number of teams
    """
    passed = True

    # Find max number of teams to calculate season length
    max_teams = max(teams_per_level.values())

    for level in levels:
        pairing_counts = {}
        n_teams = teams_per_level[level]

        # Calculate expected number of times each pairing should appear
        # For a level with n teams in a season sized for max_teams,
        # each pairing appears 2*(max_teams-1)/(n-1) times on average
        expected_count = 2 * (max_teams - 1) / (n_teams - 1)
        # Round to nearest integer if it's very close to one
        if abs(expected_count - round(expected_count)) < 0.01:
            expected_count = round(expected_count)

        # Go through all weeks for each level
        for week in schedule:
            # Check each slot
            for slot_num in range(1, 5):
                slot_key = str(slot_num)
                if slot_key not in week["slots"]:
                    continue

                # Find games in this level
                for game in week["slots"][slot_key]:
                    if game["level"] == level:
                        # Extract team names and create a sorted pair
                        team1, team2 = game["teams"]
                        pair_sorted = tuple(sorted([team1, team2]))
                        pairing_counts[pair_sorted] = (
                            pairing_counts.get(pair_sorted, 0) + 1
                        )

        # Verify each pair appears the expected number of times
        expected_pairs = n_teams * (n_teams - 1) // 2
        if len(pairing_counts) != expected_pairs:
            print(
                f"Level {level}: Found {len(pairing_counts)} pairs but expected {expected_pairs}"
            )
            passed = False

        # Check the counts
        for pair, count in pairing_counts.items():
            if count != expected_count and abs(count - expected_count) > 0.01:
                print(
                    f"Level {level}: Pair {pair} appears {count} times (expected {expected_count})"
                )
                passed = False

        if len(pairing_counts) == 0:
            print(f"Warning: No games found for level {level}")
        elif passed:
            print(
                f"Level {level}: All pairings appear {expected_count} times as expected."
            )

    return passed


def global_slot_distribution_test(schedule, expected):
    """
    Tests that each slot has the correct number of games across all levels.

    Args:
        schedule: The formatted schedule data
    """
    all_ok = True

    for week in schedule:
        week_num = week["week"]
        week_counts = {s: 0 for s in [1, 2, 3, 4]}

        # Count games in each slot
        for slot_num in range(1, 5):
            slot_key = str(slot_num)
            if slot_key in week["slots"]:
                week_counts[slot_num] = len(week["slots"][slot_key])

        if week_counts != expected:
            print(
                f"Week {week_num}: Global slot distribution incorrect: {week_counts} (expected {expected})"
            )
            all_ok = False

    if all_ok:
        print(
            "Global slot distribution test passed: Each week has the correct total games per slot."
        )

    return all_ok


def referee_player_test(schedule):
    """
    Tests that no referee is also playing in the same game.

    Args:
        schedule: The formatted schedule data
    """
    passed = True

    for week in schedule:
        week_num = week["week"]

        # Check each slot
        for slot_num in range(1, 5):
            slot_key = str(slot_num)
            if slot_key not in week["slots"]:
                continue

            # Check each game
            for game in week["slots"][slot_key]:
                level = game["level"]
                team1, team2 = game["teams"]
                referee = game["ref"]

                if referee in [team1, team2]:
                    print(
                        f"Week {week_num}, Level {level}: Referee {referee} is playing in game ({team1} vs {team2})"
                    )
                    passed = False

    if passed:
        print("All games: Referee is not playing in the same game.")

    return passed


def adjacent_slot_test(schedule):
    """
    Tests that referees only officiate in slots adjacent to their playing slot.

    Args:
        schedule: The formatted schedule data
    """
    passed = True

    for week in schedule:
        week_num = week["week"]

        # Create a mapping of teams to their playing slots for this week
        team_playing_slots = {}

        # First, find when each team is playing
        for slot_num in range(1, 5):
            slot_key = str(slot_num)
            if slot_key not in week["slots"]:
                continue

            for game in week["slots"][slot_key]:
                team1, team2 = game["teams"]
                team_playing_slots[team1] = int(slot_key)
                team_playing_slots[team2] = int(slot_key)

        # Now check referee assignments
        for slot_num in range(1, 5):
            slot_key = str(slot_num)
            if slot_key not in week["slots"]:
                continue

            for game in week["slots"][slot_key]:
                level = game["level"]
                referee = game["ref"]

                if referee in team_playing_slots:
                    ref_play_slot = team_playing_slots[referee]
                    if abs(ref_play_slot - int(slot_key)) != 1:
                        print(
                            f"Week {week_num}, Level {level}: Game in slot {slot_key} has referee {referee} "
                            f"whose playing slot is {ref_play_slot} (diff {abs(ref_play_slot - int(slot_key))})"
                        )
                        passed = False
                else:
                    print(
                        f"Week {week_num}, Level {level}: Referee {referee} not found in any pairing!"
                    )
                    passed = False

    if passed:
        print("All weeks and levels satisfy the referee adjacent-slot condition.")

    return passed


def mirror_pairing_test(schedule, first_half_weeks=5):
    """
    Tests that the second half of the schedule mirrors the matchups in the first half.
    For each level, if team A plays team B in week N, they must also play in week N+first_half_weeks.

    Args:
        schedule: The formatted schedule data
        first_half_weeks: Number of weeks in the first half (default: 5)

    Returns:
        bool: True if the mirror property is maintained, False otherwise
    """
    passed = True

    # Organize the schedule into a better format for checking
    matchups_by_week = {}
    for week in schedule:
        week_num = week["week"]
        matchups_by_week[week_num] = {}

        for slot_num in range(1, 5):
            slot_key = str(slot_num)
            if slot_key not in week["slots"]:
                continue

            for game in week["slots"][slot_key]:
                level = game["level"]
                team1, team2 = game["teams"]

                # Store each level's matchups for this week
                if level not in matchups_by_week[week_num]:
                    matchups_by_week[week_num][level] = []

                # Store as a sorted pair to ensure consistent comparison
                matchups_by_week[week_num][level].append(tuple(sorted([team1, team2])))

    # Check mirror weeks
    for first_week in range(1, first_half_weeks + 1):
        mirror_week = first_week + first_half_weeks

        if mirror_week not in matchups_by_week:
            print(f"Mirror week {mirror_week} not found in schedule")
            passed = False
            continue

        # For each level, check if matchups are mirrored
        for level in matchups_by_week[first_week]:
            if level not in matchups_by_week[mirror_week]:
                print(f"Level {level} not found in mirror week {mirror_week}")
                passed = False
                continue

            # Get matchups for both weeks
            first_matchups = set(matchups_by_week[first_week][level])
            mirror_matchups = set(matchups_by_week[mirror_week][level])

            # Check if they match
            if first_matchups != mirror_matchups:
                print(
                    f"Week {first_week} and mirror week {mirror_week} have different matchups for level {level}"
                )
                print(f"  Week {first_week} matchups: {first_matchups}")
                print(f"  Week {mirror_week} matchups: {mirror_matchups}")
                passed = False

    if passed:
        print("All mirror week matchups are preserved correctly.")

    return passed


def cycle_pairing_test(schedule, levels, teams_per_level):
    """
    Tests that teams in levels with fewer teams follow a proper cycling pattern.
    For a level with n teams in a season with max_teams teams:
    - Each round-robin takes (n-1) weeks
    - Matchups from week k should repeat in weeks k+(n-1), k+2(n-1), etc.

    Args:
        schedule: The formatted schedule data
        levels: List of competition levels (e.g., ["A", "B", "C"])
        teams_per_level: Dict mapping each level to its number of teams

    Returns:
        bool: True if all levels follow proper cycling patterns
    """
    passed = True
    max_teams = max(teams_per_level.values())
    season_weeks = 2 * (max_teams - 1)  # Total weeks in the season

    for level in levels:
        n_teams = teams_per_level[level]
        round_robin_weeks = n_teams - 1  # Weeks needed for one round-robin

        # Skip if this level has the max number of teams (standard cycle)
        if n_teams == max_teams:
            continue

        # Organize matchups by week
        matchups_by_week = {}
        for week in schedule:
            week_num = week["week"]
            if week_num not in matchups_by_week:
                matchups_by_week[week_num] = []

            for slot_num in range(1, 5):
                slot_key = str(slot_num)
                if slot_key not in week["slots"]:
                    continue

                for game in week["slots"][slot_key]:
                    if game["level"] == level:
                        team1, team2 = game["teams"]
                        pair = tuple(sorted([team1, team2]))
                        matchups_by_week[week_num].append(pair)

        # Check each base week and its repetitions
        for base_week in range(1, round_robin_weeks + 1):
            if base_week not in matchups_by_week:
                print(f"Level {level}: Week {base_week} not found in schedule")
                passed = False
                continue

            base_matchups = set(matchups_by_week[base_week])

            # Check each repetition of this base week
            for cycle in range(1, season_weeks // round_robin_weeks + 1):
                repeat_week = base_week + (cycle * round_robin_weeks)

                # Skip if beyond season length
                if repeat_week > season_weeks:
                    break

                if repeat_week not in matchups_by_week:
                    print(
                        f"Level {level}: Repeat week {repeat_week} not found in schedule"
                    )
                    passed = False
                    continue

                repeat_matchups = set(matchups_by_week[repeat_week])

                # Check if matchups are the same
                if base_matchups != repeat_matchups:
                    print(
                        f"Level {level}: Week {base_week} and week {repeat_week} should have the same matchups"
                    )
                    print(f"  Week {base_week} matchups: {base_matchups}")
                    print(f"  Week {repeat_week} matchups: {repeat_matchups}")
                    passed = False

    if passed:
        print("All levels follow proper cycling patterns for matchups")

    return passed


def run_all_tests(schedule, levels=None, teams_per_level=None):
    """
    Run all schedule tests.

    Args:
        schedule: The formatted schedule data
        levels: List of competition levels (default: ["A", "B", "C"])
        teams_per_level: Dict mapping each level to its number of teams
            (default: {"A": 6, "B": 6, "C": 6})

    Returns:
        bool: True if all tests passed, False otherwise
    """
    if levels is None:
        levels = ["A", "B", "C"]

    if teams_per_level is None:
        teams_per_level = {level: 6 for level in levels}

    print("\n=== RUNNING SCHEDULE TESTS ===\n")

    pairing_result = pairing_tests(schedule, levels, teams_per_level)
    print()

    slot_dist_result = global_slot_distribution_test(schedule, {1: 1, 2: 3, 3: 2, 4: 3})
    print()

    referee_result = referee_player_test(schedule)
    print()

    adjacent_result = adjacent_slot_test(schedule)
    print()

    cycle_result = cycle_pairing_test(schedule, levels, teams_per_level)
    print()

    mirror_result = mirror_pairing_test(schedule)
    print()

    all_passed = (
        pairing_result
        and slot_dist_result
        and referee_result
        and adjacent_result
        and cycle_result
        and mirror_result
    )

    if all_passed:
        print("All tests passed! This is a valid schedule.")
    else:
        print("Some tests failed. The schedule needs adjustment.")

    return all_passed
