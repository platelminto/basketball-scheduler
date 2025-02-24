def pairing_tests(schedule, levels, teams):
    passed = True
    for level in levels:
        pairing_counts = {}
        for week in schedule:
            _, pairing, _ = week[level]
            for pair in pairing:
                pair_sorted = tuple(sorted(pair))
                pairing_counts[pair_sorted] = pairing_counts.get(pair_sorted, 0) + 1
        for pair, count in pairing_counts.items():
            if count != 2:
                print(
                    f"Level {level}: Pair {tuple(t+1 for t in pair)} appears {count} times (expected 2)"
                )
                passed = False
        if passed:
            print(f"Level {level}: All pairings appear exactly 2 times.")
    return passed


def global_slot_distribution_test(schedule):
    expected = {1: 1, 2: 3, 3: 2, 4: 3}
    all_ok = True
    for w, week in enumerate(schedule):
        week_counts = {s: 0 for s in [1, 2, 3, 4]}
        for level in week:
            distribution, _, _ = week[level]
            for s in distribution:
                week_counts[s] += 1
        if week_counts != expected:
            print(
                f"Week {w+1}: Global slot distribution incorrect: {week_counts} (expected {expected})"
            )
            all_ok = False
    if all_ok:
        print(
            "Global slot distribution test passed: Each week has the correct total games per slot."
        )
    return all_ok


def referee_player_test(schedule):
    passed = True
    for week_idx, week in enumerate(schedule):
        for level in week:
            _, pairing, ref_assignment = week[level]
            for i in range(3):
                t1, t2 = pairing[i]
                ref = ref_assignment[i]
                if ref in (t1, t2):
                    print(
                        f"Week {week_idx+1}, Level {level}: Referee {ref+1} is playing in game ({t1+1} vs {t2+1})"
                    )
                    passed = False
    if passed:
        print("All games: Referee is not playing in the same game.")
    return passed


def adjacent_slot_test(schedule):
    passed = True
    for week_idx, week in enumerate(schedule):
        for level in week:
            distribution, pairing, ref_assignment = week[level]
            for i in range(3):
                current_slot = distribution[i]
                ref = ref_assignment[i]
                found = False
                for j in range(3):
                    if ref in pairing[j]:
                        found = True
                        ref_play_slot = distribution[j]
                        if abs(ref_play_slot - current_slot) != 1:
                            print(
                                f"Week {week_idx+1}, Level {level}: Game {i+1} (slot {current_slot}) has referee {ref+1} whose playing slot is {ref_play_slot} (diff {abs(ref_play_slot - current_slot)})"
                            )
                            passed = False
                        break
                if not found:
                    print(
                        f"Week {week_idx+1}, Level {level}: Referee {ref+1} not found in any pairing!"
                    )
                    passed = False
    if passed:
        print("All weeks and levels satisfy the referee adjacent-slot condition.")
    return passed
