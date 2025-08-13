from django.test import TestCase
from utils import convert_to_formatted_schedule, get_config_from_schedule_creator, load_schedule_from_file, save_schedule_to_file
import json
import os
import tempfile


class UtilityTests(TestCase):
    def setUp(self):
        # Create sample data for testing
        self.levels = ["A", "B"]
        self.team_names = {
            "A": ["Team A1", "Team A2", "Team A3", "Team A4"],
            "B": ["Team B1", "Team B2", "Team B3", "Team B4"]
        }
        
        # Mock schedule data
        self.schedule = [
            {  # Week 1
                "A": ([1, 1], [(0, 1), (2, 3)], [2, 3]),
                "B": ([2, 2], [(0, 1), (2, 3)], [2, 3])
            },
            {  # Week 2
                "A": ([2, 2], [(0, 2), (1, 3)], [1, 0]),
                "B": ([1, 1], [(0, 2), (1, 3)], [1, 0])
            }
        ]
        
        # Config for testing
        self.config = {
            "levels": self.levels,
            "team_names_by_level": self.team_names,
            "num_slots": 2
        }
        
        # Team setup output for testing get_config_from_schedule_creator
        self.team_setup_output = {
            "teams": {
                "A": ["Team A1", "Team A2", "Team A3", "Team A4"],
                "B": ["Team B1", "Team B2", "Team B3", "Team B4"]
            },
            "schedule": {
                "weeks": [
                    {
                        "weekNumber": 1,
                        "isOffWeek": False,
                        "days": [
                            {
                                "date": "2025-04-07",
                                "times": [
                                    {"time": "18:10", "courts": 2},
                                    {"time": "19:20", "courts": 2}
                                ]
                            }
                        ]
                    },
                    {
                        "weekNumber": 2,
                        "isOffWeek": False,
                        "days": [
                            {
                                "date": "2025-04-14",
                                "times": [
                                    {"time": "18:10", "courts": 2},
                                    {"time": "19:20", "courts": 2}
                                ]
                            }
                        ]
                    }
                ]
            }
        }

    def test_convert_to_formatted_schedule(self):
        """Test the conversion of internal schedule format to JSON format."""
        formatted_schedule = convert_to_formatted_schedule(self.schedule, self.levels, self.config)
        
        # Check structure
        self.assertEqual(len(formatted_schedule), 2)  # Two weeks
        self.assertEqual(formatted_schedule[0]["week"], 1)
        self.assertEqual(formatted_schedule[1]["week"], 2)
        
        # Check slots
        self.assertIn("1", formatted_schedule[0]["slots"])
        self.assertIn("2", formatted_schedule[0]["slots"])
        
        # Check game data for week 1
        week1_slot1_games = formatted_schedule[0]["slots"]["1"]
        self.assertEqual(len(week1_slot1_games), 2)  # 2 games in slot 1 of week 1
        
        # Check first game details
        game1 = week1_slot1_games[0]
        self.assertEqual(game1["level"], "A")
        self.assertEqual(game1["teams"], ["Team A1", "Team A2"])
        self.assertEqual(game1["ref"], "Team A3")

    def test_get_config_from_schedule_creator(self):
        """Test extracting configuration from team setup output."""
        # Extract week data from the team setup output
        week_data = {}
        for week in self.team_setup_output["schedule"]["weeks"]:
            if not week.get("isOffWeek", False):
                week_data[week["weekNumber"]] = {
                    "games": [],
                    "isOffWeek": False
                }
                # Add mock games data for each week
                for day in week.get("days", []):
                    for time_slot in day.get("times", []):
                        # Create mock games for each court/time combination
                        for court in range(time_slot["courts"]):
                            week_data[week["weekNumber"]]["games"].append({
                                "day_of_week": 1,  # Monday
                                "time": time_slot["time"]
                            })
        
        config = get_config_from_schedule_creator(self.team_setup_output, week_data)
        
        # Check extracted values
        self.assertEqual(config["levels"], ["A", "B"])
        self.assertEqual(config["teams_per_level"], {"A": 4, "B": 4})
        self.assertEqual(config["total_weeks"], 2)
        self.assertEqual(config["first_half_weeks"], 1)
        
        # Check courts per slot
        self.assertEqual(config["courts_per_slot"][1], [2, 2])  # Slot 1: 2 courts in both weeks
        self.assertEqual(config["courts_per_slot"][2], [2, 2])  # Slot 2: 2 courts in both weeks

    def test_get_config_with_offweeks(self):
        """Test that offweeks are properly handled in schedule configuration."""
        # Modify the team_setup_output to include an offweek
        setup_with_offweek = self.team_setup_output.copy()
        setup_with_offweek["schedule"] = setup_with_offweek["schedule"].copy()
        setup_with_offweek["schedule"]["weeks"] = setup_with_offweek["schedule"]["weeks"].copy()
        
        # Insert an offweek
        setup_with_offweek["schedule"]["weeks"].insert(1, {
            "weekNumber": 2,
            "isOffWeek": True,
            "date": "2025-04-14"
        })
        # Adjust the remaining week number
        weeks_copy = setup_with_offweek["schedule"]["weeks"].copy()
        weeks_copy[2] = weeks_copy[2].copy()
        weeks_copy[2]["weekNumber"] = 3
        setup_with_offweek["schedule"]["weeks"] = weeks_copy
        
        # Extract week data from the setup with offweek
        week_data = {}
        for week in setup_with_offweek["schedule"]["weeks"]:
            if not week.get("isOffWeek", False):
                week_data[week["weekNumber"]] = {
                    "games": [],
                    "isOffWeek": False
                }
                # Add mock games data for each week
                for day in week.get("days", []):
                    for time_slot in day.get("times", []):
                        # Create mock games for each court/time combination
                        for court in range(time_slot["courts"]):
                            week_data[week["weekNumber"]]["games"].append({
                                "day_of_week": 1,  # Monday
                                "time": time_slot["time"]
                            })
        
        config = get_config_from_schedule_creator(setup_with_offweek, week_data)
        
        # Should only count actual game weeks (not offweeks)
        self.assertEqual(config["total_weeks"], 2)
        self.assertEqual(config["first_half_weeks"], 1)

    def test_config_with_different_team_counts(self):
        """Test handling of configuration with different team counts per level."""
        # Create setup with different team counts
        uneven_setup = self.team_setup_output.copy()
        uneven_setup["teams"] = {
            "A": ["Team A1", "Team A2", "Team A3", "Team A4"],
            "B": ["Team B1", "Team B2", "Team B3", "Team B4", "Team B5", "Team B6"]
        }
        
        # Create week data for the uneven setup test
        week_data = {}
        for week in self.team_setup_output["schedule"]["weeks"]:
            if not week.get("isOffWeek", False):
                week_data[week["weekNumber"]] = {
                    "games": [],
                    "isOffWeek": False
                }
                # Add mock games data for each week
                for day in week.get("days", []):
                    for time_slot in day.get("times", []):
                        # Create mock games for each court/time combination
                        for court in range(time_slot["courts"]):
                            week_data[week["weekNumber"]]["games"].append({
                                "day_of_week": 1,  # Monday
                                "time": time_slot["time"]
                            })
        
        # This should raise a ValueError
        with self.assertRaises(ValueError) as context:
            get_config_from_schedule_creator(uneven_setup, week_data)
        
        self.assertTrue("same number of teams" in str(context.exception))

    def test_save_and_load_schedule(self):
        """Test saving and loading a schedule to/from a file."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_schedule.json")
            
            # Format the schedule
            formatted_schedule = convert_to_formatted_schedule(self.schedule, self.levels, self.config)
            
            # Save the schedule
            save_result = save_schedule_to_file(formatted_schedule, self.config, test_file)
            self.assertTrue(save_result)
            self.assertTrue(os.path.exists(test_file))
            
            # Load the schedule
            loaded_schedule = load_schedule_from_file(test_file)
            self.assertIsNotNone(loaded_schedule)
            
            # Check that loaded schedule matches the original
            self.assertEqual(len(loaded_schedule), len(formatted_schedule))
            self.assertEqual(loaded_schedule[0]["week"], formatted_schedule[0]["week"])
            
            # Check for the teams file
            teams_file = f"{os.path.splitext(test_file)[0]}_teams.json"
            self.assertTrue(os.path.exists(teams_file))
            
            # Load and check teams file
            with open(teams_file, 'r') as f:
                teams_data = json.load(f)
                self.assertEqual(teams_data["levels"], self.levels)
                self.assertEqual(teams_data["teams_by_level"], self.team_names)
            
            # Test loading non-existent file
            nonexistent_file = os.path.join(temp_dir, "nonexistent.json")
            self.assertIsNone(load_schedule_from_file(nonexistent_file))