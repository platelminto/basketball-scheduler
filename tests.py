def pairing_tests(schedule, levels, teams):
    """
    Tests that each team pair plays exactly twice during the season.

    Args:
        schedule: The formatted schedule data
        levels: List of competition levels (e.g., ["A", "B", "C"])
        teams: Number of teams per level
    """
    passed = True

    for level in levels:
        pairing_counts = {}

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

        # Verify each pair appears exactly twice
        for pair, count in pairing_counts.items():
            if count != 2:
                print(f"Level {level}: Pair {pair} appears {count} times (expected 2)")
                passed = False

        if len(pairing_counts) == 0:
            print(f"Warning: No games found for level {level}")
        elif passed:
            print(f"Level {level}: All pairings appear exactly 2 times.")

    return passed


def global_slot_distribution_test(schedule):
    """
    Tests that each slot has the correct number of games across all levels.

    Args:
        schedule: The formatted schedule data
    """
    expected = {1: 1, 2: 3, 3: 2, 4: 3}
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


def run_all_tests(schedule, levels=None, teams_per_level=6):
    """
    Run all schedule tests.

    Args:
        schedule: The formatted schedule data
        levels: List of competition levels (default: ["A", "B", "C"])
        teams_per_level: Number of teams per level (default: 6)

    Returns:
        bool: True if all tests passed, False otherwise
    """
    if levels is None:
        levels = ["A", "B", "C"]

    print("\n=== RUNNING SCHEDULE TESTS ===\n")

    pairing_result = pairing_tests(schedule, levels, teams_per_level)
    print()

    slot_dist_result = global_slot_distribution_test(schedule)
    print()

    referee_result = referee_player_test(schedule)
    print()

    adjacent_result = adjacent_slot_test(schedule)
    print()

    all_passed = (
        pairing_result and slot_dist_result and referee_result and adjacent_result
    )

    if all_passed:
        print("All tests passed! This is a valid schedule.")
    else:
        print("Some tests failed. The schedule needs adjustment.")

    return all_passed
