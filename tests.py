def pairing_tests(schedule, levels, teams_per_level):
    """
    Tests that each team pair plays the correct number of times during the season.
    When levels have different team counts, pairings may occur more than twice.

    Args:
        schedule: The formatted schedule data
        levels: List of competition levels (e.g., ["A", "B", "C"])
        teams_per_level: Dict mapping each level to its number of teams

    Returns:
        tuple[bool, list[str]]: A tuple containing a boolean indicating if the test passed
                                and a list of error/warning messages.
    """
    passed = True
    errors = []  # Initialize list to store error messages

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
            # Check each slot that exists in the week's data
            for slot_key, games in week["slots"].items():
                # Find games in this level
                for game in games:
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
            message = f"Level {level}: Found {len(pairing_counts)} pairs but expected {expected_pairs}"
            print(message)
            errors.append(message)
            passed = False

        # Check the counts
        for pair, count in pairing_counts.items():
            if count != expected_count and abs(count - expected_count) > 0.01:
                message = f"Level {level}: Pair {pair} appears {count} times (expected {expected_count})"
                print(message)
                errors.append(message)
                passed = False

        if len(pairing_counts) == 0:
            message = f"Warning: No games found for level {level}"
            print(message)
            errors.append(message)  # Include warnings in the list
        elif (
            passed and not errors
        ):  # Check errors list to avoid double printing success
            print(
                f"Level {level}: All pairings appear {expected_count} times as expected."
            )

    return passed, errors


def global_slot_distribution_test(schedule, expected_courts_per_slot, num_slots):
    """
    Tests that each slot has the correct number of games across all levels for each week.

    Args:
        schedule: The formatted schedule data
        expected_courts_per_slot: Dict mapping slots to lists of expected court counts by week

    Returns:
        tuple[bool, list[str]]: A tuple containing a boolean indicating if the test passed
                                and a list of error messages.
    """
    all_ok = True
    errors = []  # Initialize list to store error messages

    for week in schedule:
        week_num = week["week"]
        week_idx = week_num - 1  # Convert 1-based week to 0-based index
        week_counts = {s: 0 for s in range(1, num_slots + 1)}

        # Count games in each slot
        for slot_num in range(1, num_slots + 1):
            slot_key = str(slot_num)
            if slot_key in week["slots"]:
                week_counts[slot_num] = len(week["slots"][slot_key])

        # Check against expected values for this week
        expected_this_week = {
            s: expected_courts_per_slot[s][week_idx] for s in expected_courts_per_slot
        }

        if week_counts != expected_this_week:
            message = (
                f"Week {week_num}: Global slot distribution incorrect: {week_counts} "
                f"(expected {expected_this_week})"
            )
            print(message)
            errors.append(message)
            all_ok = False

    if all_ok:
        print(
            "Global slot distribution test passed: Each week has the correct total games per slot."
        )

    return all_ok, errors


def referee_player_test(schedule):
    """
    Tests that no referee is also playing in the same game.

    Args:
        schedule: The formatted schedule data

    Returns:
        tuple[bool, list[str]]: A tuple containing a boolean indicating if the test passed
                                and a list of error messages.
    """
    passed = True
    errors = []  # Initialize list to store error messages

    for week in schedule:
        week_num = week["week"]

        # Check each slot present in the week
        for slot_key, games in week["slots"].items():
            # Check each game
            for game in games:
                level = game["level"]
                team1, team2 = game["teams"]
                referee = game["ref"]

                if referee in [team1, team2]:
                    message = f"Week {week_num}, Level {level}: Referee {referee} is playing in game ({team1} vs {team2})"
                    print(message)
                    errors.append(message)
                    passed = False

    if passed:
        print("All games: Referee is not playing in the same game.")

    return passed, errors


def adjacent_slot_test(schedule):
    """
    Tests that referees only officiate in slots adjacent to their playing slot.

    Args:
        schedule: The formatted schedule data

    Returns:
        tuple[bool, list[str]]: A tuple containing a boolean indicating if the test passed
                                and a list of error messages.
    """
    passed = True
    errors = []  # Initialize list to store error messages

    for week in schedule:
        week_num = week["week"]

        # Create a mapping of teams to their playing slots for this week
        team_playing_slots = {}

        # First, find when each team is playing by iterating through existing slots
        for slot_key, games in week["slots"].items():
            slot_num = int(slot_key)  # Keep slot_num as an integer for comparison later
            for game in games:
                team1, team2 = game["teams"]
                team_playing_slots[team1] = slot_num
                team_playing_slots[team2] = slot_num

        # Now check referee assignments by iterating through existing slots
        for slot_key, games in week["slots"].items():
            slot_num = int(slot_key)  # Keep slot_num as an integer for comparison
            for game in games:
                level = game["level"]
                referee = game["ref"]

                if referee in team_playing_slots:
                    ref_play_slot = team_playing_slots[referee]
                    # Check if the absolute difference between the ref's playing slot and the current game's slot is not 1
                    if abs(ref_play_slot - slot_num) != 1:
                        message = (
                            f"Week {week_num}, Level {level}: Game in slot {slot_num} has referee {referee} "
                            f"whose playing slot is {ref_play_slot} (diff {abs(ref_play_slot - slot_num)})"
                        )
                        print(message)
                        errors.append(message)
                        passed = False
                else:
                    # If referee is not in team_playing_slots, assume it's an external referee
                    # External referees don't need to follow the adjacent slot rule
                    message = f"Week {week_num}, Level {level}: External referee '{referee}' used (not a team)"
                    print(message)
                    # Don't add to errors or set passed=False since this is expected behavior

    if passed:
        print("All weeks and levels satisfy the referee adjacent-slot condition.")

    return passed, errors


def mirror_pairing_test(schedule, first_half_weeks=5):
    """
    Tests that the second half of the schedule mirrors the matchups in the first half.
    For each level, if team A plays team B in week N, they must also play in week N+first_half_weeks.

    Args:
        schedule: The formatted schedule data
        first_half_weeks: Number of weeks in the first half (default: 5)

    Returns:
        tuple[bool, list[str]]: A tuple containing a boolean indicating if the test passed
                                and a list of error messages.
    """
    passed = True
    errors = []  # Initialize list to store error messages

    # Organize the schedule into a better format for checking
    matchups_by_week = {}
    for week in schedule:
        week_num = week["week"]
        matchups_by_week[week_num] = {}

        # Iterate through existing slots
        for slot_key, games in week["slots"].items():
            for game in games:
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

        if first_week not in matchups_by_week:
            # If the first week doesn't exist, we can't check its mirror
            message = f"Warning: Data for week {first_week} not found, cannot check mirror week {mirror_week}."
            print(message)
            errors.append(message)
            continue  # Skip to the next week

        if mirror_week not in matchups_by_week:
            message = f"Mirror week {mirror_week} (for week {first_week}) not found in schedule"
            print(message)
            errors.append(message)
            passed = False
            continue

        # For each level, check if matchups are mirrored
        for level in matchups_by_week[first_week]:
            if level not in matchups_by_week[mirror_week]:
                message = f"Level {level} not found in mirror week {mirror_week} (present in week {first_week})"
                print(message)
                errors.append(message)
                passed = False
                continue

            # Get matchups for both weeks
            first_matchups = set(matchups_by_week[first_week][level])
            mirror_matchups = set(matchups_by_week[mirror_week][level])

            # Check if they match
            if first_matchups != mirror_matchups:
                message = f"Week {first_week} and mirror week {mirror_week} have different matchups for level {level}"
                print(message)
                errors.append(message)
                # Add details about the differences for better debugging
                diff1 = first_matchups - mirror_matchups
                diff2 = mirror_matchups - first_matchups
                if diff1:
                    errors.append(f"  Only in Week {first_week}: {diff1}")
                    print(f"  Only in Week {first_week}: {diff1}")
                if diff2:
                    errors.append(f"  Only in Week {mirror_week}: {diff2}")
                    print(f"  Only in Week {mirror_week}: {diff2}")

                passed = False

        # Check for levels present in mirror week but not first week (less likely but possible)
        if passed:  # Only check if the other direction hasn't already failed
            for level in matchups_by_week[mirror_week]:
                if level not in matchups_by_week[first_week]:
                    message = f"Level {level} found in mirror week {mirror_week} but not in base week {first_week}"
                    print(message)
                    errors.append(message)
                    passed = False

    if passed:
        print("All mirror week matchups are preserved correctly.")

    return passed, errors


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
        tuple[bool, list[str]]: A tuple containing a boolean indicating if the test passed
                                and a list of error messages.
    """
    passed = True
    errors = []  # Initialize list to store error messages
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

            # Iterate through existing slots
            for slot_key, games in week["slots"].items():
                for game in games:
                    if game["level"] == level:
                        team1, team2 = game["teams"]
                        pair = tuple(sorted([team1, team2]))
                        matchups_by_week[week_num].append(pair)

        # Check each base week and its repetitions
        for base_week in range(1, round_robin_weeks + 1):
            if base_week not in matchups_by_week:
                message = (
                    f"Level {level}: Base week {base_week} not found in schedule data"
                )
                print(message)
                errors.append(message)
                passed = False  # Cannot check cycles if base week is missing
                continue

            base_matchups = set(matchups_by_week[base_week])

            # Check each repetition of this base week
            for cycle in range(
                1, season_weeks // round_robin_weeks + 1
            ):  # Use ceiling division? No, floor is correct.
                repeat_week = base_week + (cycle * round_robin_weeks)

                # Skip if beyond season length according to max_teams
                if repeat_week > season_weeks:
                    # Check if this week *unexpectedly* exists in the schedule data
                    if repeat_week in matchups_by_week:
                        message = f"Level {level}: Week {repeat_week} exists but should be beyond season length ({season_weeks})"
                        print(message)
                        errors.append(message)
                        # It's extra data, maybe not strictly a cycle failure, but worth noting.
                    break  # Stop checking cycles for this base_week

                if repeat_week not in matchups_by_week:
                    message = f"Level {level}: Expected repeat week {repeat_week} (cycle {cycle} of week {base_week}) not found in schedule"
                    print(message)
                    errors.append(message)
                    passed = False
                    continue  # Continue checking other cycles for this base week if possible

                repeat_matchups = set(matchups_by_week[repeat_week])

                # Check if matchups are the same
                if base_matchups != repeat_matchups:
                    message = f"Level {level}: Week {base_week} and repeat week {repeat_week} should have the same matchups but differ"
                    print(message)
                    errors.append(message)
                    # Add details about the differences
                    diff1 = base_matchups - repeat_matchups
                    diff2 = repeat_matchups - base_matchups
                    if diff1:
                        errors.append(f"  Only in Week {base_week}: {diff1}")
                        print(f"  Only in Week {base_week}: {diff1}")
                    if diff2:
                        errors.append(f"  Only in Week {repeat_week}: {diff2}")
                        print(f"  Only in Week {repeat_week}: {diff2}")
                    passed = False

    if passed:
        print("All levels follow proper cycling patterns for matchups")

    return passed, errors
