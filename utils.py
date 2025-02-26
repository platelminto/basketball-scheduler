import json
import os


def convert_to_formatted_schedule(schedule, levels):
    """Convert internal schedule format to the standardized JSON format"""
    # Create a dictionary of team names by level
    team_names_by_level = {
        "A": [f"HighTeam{i+1}" for i in range(6)],
        "B": [f"MidTeam{i+1}" for i in range(6)],
        "C": [f"LowTeam{i+1}" for i in range(6)],
    }

    def team_name(team_idx, level):
        if level in team_names_by_level and 0 <= team_idx < len(
            team_names_by_level[level]
        ):
            return team_names_by_level[level][team_idx]
        return f"{level}{team_idx + 1}"  # Fallback

    # Restructure the schedule for better readability
    formatted_schedule = []

    for week_num, week in enumerate(schedule, 1):
        week_data = {"week": week_num, "slots": {}}

        # Organize games by slot
        for slot in range(1, 5):
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
                        team_name(team1_idx, level),
                        team_name(team2_idx, level),
                    ],
                    "ref": team_name(ref, level),
                }
                week_data["slots"][str(slot)].append(game)

        formatted_schedule.append(week_data)

    return formatted_schedule


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


def save_schedule_to_file(schedule, filename="saved_schedule.json"):
    """Save a schedule to a JSON file with descriptive team names and level/team information"""
    try:
        # Create a dictionary of team names by level
        team_names_by_level = {
            "A": [f"HighTeam{i+1}" for i in range(6)],
            "B": [f"MidTeam{i+1}" for i in range(6)],
            "C": [f"LowTeam{i+1}" for i in range(6)],
        }

        with open(filename, "w") as f:
            json.dump(schedule, f, indent=2)

        # Save team information in a separate file
        team_info = {"levels": ["A", "B", "C"], "teams_by_level": team_names_by_level}

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
