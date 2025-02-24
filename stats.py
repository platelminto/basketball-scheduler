import math


def compute_games_per_slot(schedule, levels):
    counts = {level: {s: 0 for s in [1, 2, 3, 4]} for level in levels}
    for week in schedule:
        for level in week:
            distribution, _, _ = week[level]
            for slot in distribution:
                counts[level][slot] += 1
    return counts


def compute_team_play_counts(schedule, teams, levels):
    counts = {
        level: {t: {s: 0 for s in [1, 2, 3, 4]} for t in teams} for level in levels
    }
    for week in schedule:
        for level in week:
            distribution, pairing, _ = week[level]
            for i in range(3):
                slot = distribution[i]
                t1, t2 = pairing[i]
                counts[level][t1][slot] += 1
                counts[level][t2][slot] += 1
    return counts


def compute_team_ref_counts(schedule, teams, levels):
    counts = {
        level: {t: {s: 0 for s in [1, 2, 3, 4]} for t in teams} for level in levels
    }
    for week in schedule:
        for level in week:
            distribution, _, ref_assignment = week[level]
            for i in range(3):
                slot = distribution[i]
                ref = ref_assignment[i]
                counts[level][ref][slot] += 1
    return counts


def print_statistics(schedule, teams, levels):
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
        for t in sorted(play_counts[level]):
            counts = play_counts[level][t]
            counts_str = ", ".join(f"Slot {s}: {counts[s]}" for s in sorted(counts))
            print(f"  Team {t+1}: {counts_str}")

    print("\nTeam Referee Counts (number of times a team referees, by slot):")
    for level in team_ref:
        print(f"Level {level}:")
        for t in sorted(team_ref[level]):
            counts = team_ref[level][t]
            total = sum(counts.values())
            counts_str = ", ".join(f"Slot {s}: {counts[s]}" for s in sorted(counts))
            print(f"  Team {t+1}: {total} times ( {counts_str} )")

    print("\nBalance Statistics (Referee counts per team):")
    for level in overall_ref:
        vals = list(overall_ref[level].values())
        mean = sum(vals) / len(vals)
        variance = sum((x - mean) ** 2 for x in vals) / len(vals)
        stddev = math.sqrt(variance)
        print(f"Level {level}: Mean = {mean:.2f}, StdDev = {stddev:.2f}")


def compute_overall_ref_counts(schedule, teams, levels):
    counts = {level: {t: 0 for t in teams} for level in levels}
    for week in schedule:
        for level in week:
            _, _, ref_assignment = week[level]
            for r in ref_assignment:
                counts[level][r] += 1
    return counts
