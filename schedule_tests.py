import unittest
from schedule_old import Scheduler
from tests import pairing_tests, referee_player_test, adjacent_slot_test

class ScheduleGenerationTests(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Use default config by not passing any arguments
        self.scheduler = Scheduler()
        
        # For validation tests
        self.levels = ["A", "B"]
        self.teams_per_level = {"A": 4, "B": 4}

    def test_round_robin_generation(self):
        """Test that the round-robin generation creates valid pairings."""
        # For 4 teams, we should get 3 rounds with 2 pairings each
        round_robin = self.scheduler.generate_round_robin_pairings(4)
        
        # Check structure
        self.assertEqual(len(round_robin), 3)  # 3 rounds for 4 teams
        for round_pairings in round_robin:
            self.assertEqual(len(round_pairings), 2)  # 2 pairings per round
        
        # Check that all pairs appear once
        pairs = []
        for round_pairings in round_robin:
            for pair in round_pairings:
                sorted_pair = tuple(sorted(pair))
                pairs.append(sorted_pair)
        
        # There should be 6 unique pairs (each team plays every other team once)
        expected_pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        actual_pairs = sorted([tuple(sorted(p)) for p in pairs])
        self.assertEqual(len(set(actual_pairs)), len(expected_pairs), 
                         f"Expected {len(expected_pairs)} unique pairs, got {len(set(actual_pairs))}")
        
        # Each team should appear in 3 different pairings
        for team in range(4):
            appearances = sum(team in pair for pair in pairs)
            self.assertEqual(appearances, 3)

    def test_schedule_validation(self):
        """Test validation functions with a valid schedule."""
        # Create a simple pre-defined valid schedule
        formatted_schedule = [
            {
                "week": 1,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["A1", "A2"],
                            "ref": "A3"
                        },
                        {
                            "level": "B",
                            "teams": ["B1", "B2"],
                            "ref": "B3"
                        }
                    ],
                    "2": [
                        {
                            "level": "A",
                            "teams": ["A3", "A4"],
                            "ref": "A1"
                        },
                        {
                            "level": "B",
                            "teams": ["B3", "B4"],
                            "ref": "B1"
                        }
                    ]
                }
            },
            {
                "week": 2,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["A1", "A3"],
                            "ref": "A4"
                        },
                        {
                            "level": "B",
                            "teams": ["B1", "B3"],
                            "ref": "B4"
                        }
                    ],
                    "2": [
                        {
                            "level": "A",
                            "teams": ["A2", "A4"],
                            "ref": "A3"
                        },
                        {
                            "level": "B",
                            "teams": ["B2", "B4"],
                            "ref": "B3"
                        }
                    ]
                }
            }
        ]
        
        # Run individual validation tests
        referee_result, referee_errors = referee_player_test(formatted_schedule)
        adjacent_result, adjacent_errors = adjacent_slot_test(formatted_schedule)
        
        # Assert that validations pass
        self.assertTrue(referee_result, f"Referee test failed with errors: {referee_errors}")
        self.assertTrue(adjacent_result, f"Adjacent slot test failed with errors: {adjacent_errors}")

    def test_invalid_schedule_detection(self):
        """Test that the validation detects invalid schedules."""
        # Create an invalid schedule (referee is playing in same game)
        invalid_schedule = [
            {
                "week": 1,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["A1", "A2"],
                            "ref": "A1"  # A1 is both playing and refereeing
                        }
                    ]
                }
            }
        ]
        
        # Run referee validation
        referee_result, referee_errors = referee_player_test(invalid_schedule)
        
        # Assert validation failure
        self.assertFalse(referee_result)
        self.assertTrue(any("Referee A1 is playing in game" in error for error in referee_errors))

if __name__ == "__main__":
    unittest.main()