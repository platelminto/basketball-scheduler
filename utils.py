import json
import os


def convert_to_formatted_schedule(schedule, levels, config):
    """Convert internal schedule format to a more understandable format"""

    team_names_by_level = config["team_names_by_level"]

    # Restructure the schedule for better readability
    formatted_schedule = []

    for week_num, week in enumerate(schedule, 1):
        week_data = {"week": week_num, "slots": {}}

        # Organize games by slot - use the configured number of slots
        for slot in range(1, config["num_slots"] + 1):
            week_data["slots"][str(slot)] = []

        # Populate slots with games
        for level in levels:
            distribution, pairing, ref_assignment = week[level]
            for game_idx, (slot, pair, ref) in enumerate(
                zip(distribution, pairing, ref_assignment)
            ):
                team1_idx, team2_idx = pair
                game = {
                    "level": level,
                    "teams": [
                        team_names_by_level[level][team1_idx],
                        team_names_by_level[level][team2_idx],
                    ],
                    "ref": team_names_by_level[level][ref],
                }
                week_data["slots"][str(slot)].append(game)

        formatted_schedule.append(week_data)

    return formatted_schedule


def get_config_from_schedule_creator(team_setup, week_data) -> dict:
    config = {}

    if len(set(len(team_names) for team_names in team_setup["teams"].values())) != 1:
        raise ValueError(
            "All levels must have the same number of teams to use the auto-generated schedule"
        )

    config["levels"] = list(team_setup["teams"].keys())

    config["teams_per_level"] = {
        level: len(team_names) for level, team_names in team_setup["teams"].items()
    }

    weeks = [week for week in week_data.values() if not week.get("isOffWeek", False)]

    # check all weeks only have 1 day
    for week in weeks:
        if len(set(game["day_of_week"] for game in week["games"])) != 1:
            raise ValueError(
                "All weeks must have only 1 day to use the auto-generated schedule"
            )

    # check all days have the same number of slots
    n_slots = len(set(game["time"] for game in weeks[0]["games"]))
    for week in weeks:
        current_n_slots = len(set(game["time"] for game in week["games"]))
        if current_n_slots != n_slots:
            raise ValueError(
                "All days must have the same number of timeslots to use the auto-generated schedule"
            )

    # how many different times are there? check first week,
    courts_per_slot = {i: [] for i in range(1, n_slots + 1)}
    for week in weeks:
        times = set(game["time"] for game in week["games"])
        times = sorted(times, key=lambda x: int(x.split(":")[0]) * 60 + int(x.split(":")[1]))
        
        for i, time in enumerate(times):
            courts_per_slot[i + 1].append(len([game for game in week["games"] if game["time"] == time]))

    config["courts_per_slot"] = courts_per_slot

    config["team_names_by_level"] = team_setup["teams"]

    config["total_weeks"] = len(weeks)

    config["first_half_weeks"] = len(weeks) // 2

    return config


def load_schedule_from_file(filename="saved_schedule.json"):
    """Load a schedule from a JSON file if it exists"""
    if not os.path.exists(filename):
        print(f"No saved schedule found at {filename}")
        return None

    try:
        with open(filename, "r") as f:
            formatted_schedule = json.load(f)

        print(f"Schedule loaded from {filename}")
        return formatted_schedule  # Return directly in the new format
    except Exception as e:
        print(f"Error loading schedule: {e}")
        return None


def save_schedule_to_file(schedule, config, filename="saved_schedule.json"):
    """Save a schedule to a JSON file with descriptive team names and level/team information"""
    try:
        with open(filename, "w") as f:
            json.dump(schedule, f, indent=2)

        # Save team information in a separate file
        team_info = {
            "levels": config["levels"],
            "teams_by_level": config["team_names_by_level"],
        }

        with open(f"{os.path.splitext(filename)[0]}_teams.json", "w") as f:
            json.dump(team_info, f, indent=2)

        print(f"Schedule saved to {filename}")
        print(f"Team information saved to {os.path.splitext(filename)[0]}_teams.json")
        return True
    except Exception as e:
        print(f"Error saving schedule: {e}")
        return False


def print_schedule(schedule_data):
    """
    Print the formatted schedule in a readable format.

    Args:
        schedule_data: The formatted schedule data (list of weeks with slot information)
    """
    print("\n=== FULL SCHEDULE ===")

    # Iterate through each week
    for week in schedule_data:
        week_num = week["week"]
        print(f"\nWEEK {week_num}")
        print("-" * 50)

        # Iterate through each slot (1-4)
        for slot_num in range(1, 5):
            slot_key = str(slot_num)

            # Skip slots with no games
            if slot_key not in week["slots"] or not week["slots"][slot_key]:
                continue

            print(f"\nSlot {slot_num}:")

            # Print each game in this slot
            for game in week["slots"][slot_key]:
                level = game["level"]
                team1, team2 = game["teams"]
                referee = game["ref"]

                print(f"  {level}: {team1} vs {team2} (Ref: {referee})")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    team_setup_output = """
{"schedule":{"weeks":[{"weekNumber":1,"isOffWeek":false,"days":[{"date":"2025-04-07","times":[{"time":"18:10","courts":3},{"time":"19:20","courts":2},{"time":"20:30","courts":1},{"time":"21:40","courts":3}]}]},{"weekNumber":2,"isOffWeek":true,"date":"2025-04-14"},{"weekNumber":3,"isOffWeek":false,"days":[{"date":"2025-04-21","times":[{"time":"18:10","courts":2},{"time":"19:20","courts":2},{"time":"20:30","courts":1},{"time":"21:40","courts":3}]}]},{"weekNumber":4,"isOffWeek":false,"days":[{"date":"2025-04-28","times":[{"time":"18:10","courts":2},{"time":"19:20","courts":2},{"time":"20:30","courts":1},{"time":"21:40","courts":3}]}]}]},"teams":{"Mid":["TeamMid1","TeamMid2","TeamMid3","TeamMid4","TeamMid5","TeamMid6","TeamMid7","TeamMid8"],"High":["TeamHigh1","TeamHigh2","TeamHigh3","TeamHigh4","TeamHigh5","TeamHigh6","TeamHigh7","TeamHigh8"],"Top":["TeamTop1","TeamTop2","TeamTop3","TeamTop4","TeamTop5","TeamTop6","TeamTop7","TeamTop8"]},"courts":["Court1","Court2","Court3"]}""".replace(
        "\n", ""
    )
    get_config_from_schedule_creator(team_setup_output)
