def pairing_tests(schedule, teams_per_level):
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

    # Find actual season length from schedule
    season_length = len(schedule)

    for level, teams in teams_per_level.items():
        pairing_counts = {}
        n_teams = len(teams)

        # Calculate expected number of times each pairing should appear
        # Based on cyclical schedule: each pairing appears once per round-robin cycle
        round_robin_length = n_teams - 1 if n_teams % 2 == 0 else n_teams
        complete_cycles = season_length // round_robin_length
        extra_weeks = season_length % round_robin_length
        
        # Base count from complete cycles
        base_count = complete_cycles
        # Some pairings get +1 from extra weeks (those that appear in first 'extra_weeks' weeks)
        expected_count_float = base_count + (extra_weeks / round_robin_length)
        
        # Calculate total games for this level (each team plays once per week)
        total_level_games = n_teams * season_length // 2
        expected_pairs = n_teams * (n_teams - 1) // 2
        
        # Calculate how many pairs should get floor vs ceil count
        min_count = int(expected_count_float)
        max_count = min_count + 1
        
        # If fractional, some pairs get min_count, others get max_count
        if abs(expected_count_float - min_count) < 0.01:
            # Very close to integer - all pairs should have same count
            expected_min_pairs = expected_pairs
            expected_max_pairs = 0
            expected_count = min_count
        else:
            # Fractional - calculate distribution
            total_min_games = expected_pairs * min_count
            extra_games_needed = total_level_games - total_min_games
            expected_max_pairs = extra_games_needed
            expected_min_pairs = expected_pairs - expected_max_pairs

        # Go through all weeks for each level
        for week in schedule:
            # Check each slot that exists in the week's data
            for slot_key, games in week["slots"].items():
                # Find games in this level
                for game in games:
                    if str(game["level"]) == level:
                        # Extract team names and create a sorted pair
                        team1, team2 = game["teams"]
                        pair_sorted = tuple(sorted([team1, team2]))
                        pairing_counts[pair_sorted] = (
                            pairing_counts.get(pair_sorted, 0) + 1
                        )

        # Verify we have the right number of pairs
        if len(pairing_counts) != expected_pairs:
            message = f"Level {level}: Found {len(pairing_counts)} pairs but expected {expected_pairs}"
            print(message)
            errors.append(message)
            passed = False

        # Check the count distribution
        if abs(expected_count_float - min_count) < 0.01:
            # All pairs should have the same count
            for pair, count in pairing_counts.items():
                if count != expected_count:
                    message = f"Level {level}: Pair {pair} appears {count} times (expected {expected_count})"
                    print(message)
                    errors.append(message)
                    passed = False
        else:
            # Check fractional distribution
            actual_min_pairs = sum(1 for count in pairing_counts.values() if count == min_count)
            actual_max_pairs = sum(1 for count in pairing_counts.values() if count == max_count)
            invalid_pairs = sum(1 for count in pairing_counts.values() if count != min_count and count != max_count)
            
            if invalid_pairs > 0:
                message = f"Level {level}: {invalid_pairs} pairs have invalid counts (should be {min_count} or {max_count})"
                print(message)
                errors.append(message)
                passed = False
            
            if actual_min_pairs != expected_min_pairs or actual_max_pairs != expected_max_pairs:
                message = f"Level {level}: Count distribution incorrect. Expected {expected_min_pairs} pairs with {min_count} games and {expected_max_pairs} pairs with {max_count} games, but got {actual_min_pairs} and {actual_max_pairs}"
                print(message)
                errors.append(message)
                passed = False

        if len(pairing_counts) == 0:
            message = f"Warning: No games found for level {level}"
            print(message)
            errors.append(message)  # Include warnings in the list
        elif passed and not any(level in error for error in errors):
            # Check if this level had any errors
            if abs(expected_count_float - min_count) < 0.01:
                print(f"Level {level}: All pairings appear {expected_count} times as expected.")
            else:
                print(f"Level {level}: Pairings distributed correctly: {expected_min_pairs} pairs with {min_count} games, {expected_max_pairs} pairs with {max_count} games.")

    return passed, errors


def global_slot_distribution_test(schedule, expected_courts_per_slot: dict[int, list[int]]):
    """
    Tests that each slot has the correct number of games across all levels for each week.

    Args:
        schedule: The formatted schedule data
        expected_courts_per_slot: Dict mapping slots to lists of expected court counts by week

    Returns:
        tuple[bool, list[str]]: A tuple containing a boolean indicating if the test passed
                                and a list of error messages.
    """
    num_slots = len(expected_courts_per_slot)
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

def cycle_pairing_test(schedule, teams_per_level):
    """
    Tests that teams follow a proper cycling pattern based on their level's round-robin length.
    For a level with n teams:
    - Each round-robin takes (n-1) weeks if n is even, or n weeks if n is odd
    - Matchups from week k should repeat in weeks k+round_robin_length, k+2*round_robin_length, etc.

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
    
    # Get actual week numbers from schedule (excluding any off weeks or gaps)
    actual_weeks = [week["week"] for week in schedule]
    actual_weeks.sort()

    for level, teams in teams_per_level.items():
        n_teams = len(teams)
        # Calculate round robin length correctly
        round_robin_weeks = n_teams - 1 if n_teams % 2 == 0 else n_teams

        # Test all levels, not just those with fewer teams

        # Organize matchups by actual schedule position (ignoring week numbers)
        matchups_by_position = {}
        position = 0
        for week in schedule:
            matchups_by_position[position] = []
            
            # Iterate through existing slots
            for slot_key, games in week["slots"].items():
                for game in games:
                    if game["level"] == level:
                        team1, team2 = game["teams"]
                        pair = tuple(sorted([team1, team2]))
                        matchups_by_position[position].append(pair)
            position += 1

        # Only test if we have enough weeks for at least 2 cycles
        total_positions = len(schedule)
        if total_positions < round_robin_weeks * 2:
            continue  # Skip testing if not enough weeks for a complete cycle

        # Check each base position and its repetitions
        for base_pos in range(round_robin_weeks):
            if base_pos not in matchups_by_position:
                continue  # Skip if no games in this position

            base_matchups = set(matchups_by_position[base_pos])
            if not base_matchups:  # Skip if no games for this level in this week
                continue

            # Check each repetition of this base position
            cycle = 1
            while True:
                repeat_pos = base_pos + (cycle * round_robin_weeks)
                
                # Stop if beyond schedule length
                if repeat_pos >= total_positions:
                    break

                if repeat_pos not in matchups_by_position:
                    break  # No more schedule data

                repeat_matchups = set(matchups_by_position[repeat_pos])
                
                # Check if matchups are the same - they should be identical pairs since we sort them
                if base_matchups != repeat_matchups:
                    actual_week_base = schedule[base_pos]["week"]
                    actual_week_repeat = schedule[repeat_pos]["week"]
                    message = f"Level {level}: Position {base_pos} (week {actual_week_base}) and repeat position {repeat_pos} (week {actual_week_repeat}) should have the same matchups but differ"
                    print(message)
                    errors.append(message)
                    # Add details about the differences
                    diff1 = base_matchups - repeat_matchups
                    diff2 = repeat_matchups - base_matchups
                    if diff1:
                        errors.append(f"  Only in position {base_pos}: {diff1}")
                        print(f"  Only in position {base_pos}: {diff1}")
                    if diff2:
                        errors.append(f"  Only in position {repeat_pos}: {diff2}")
                        print(f"  Only in position {repeat_pos}: {diff2}")
                    passed = False
                
                cycle += 1

    if passed:
        print("All levels follow proper cycling patterns for matchups")

    return passed, errors

