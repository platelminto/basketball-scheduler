from django.test import TestCase, Client
from django.urls import reverse
from .models import Season, Level, Team, Game
from utils import convert_to_formatted_schedule, get_config_from_schedule_creator, load_schedule_from_file, save_schedule_to_file
import json
import os
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
import tempfile
from datetime import datetime, timedelta
from django.utils import timezone


class ModelTests(TestCase):
    def setUp(self):
        # Create a test season
        self.season = Season.objects.create(name="Test Season", is_active=True)
        # Create levels
        self.level_a = Level.objects.create(season=self.season, name="A")
        self.level_b = Level.objects.create(season=self.season, name="B")
        # Create teams
        self.team_a1 = Team.objects.create(level=self.level_a, name="Team A1")
        self.team_a2 = Team.objects.create(level=self.level_a, name="Team A2")
        self.team_b1 = Team.objects.create(level=self.level_b, name="Team B1")
        self.team_b2 = Team.objects.create(level=self.level_b, name="Team B2")

    def test_season_active_constraint(self):
        """Test that only one season can be active at a time."""
        new_season = Season.objects.create(name="New Season", is_active=True)
        # Refresh the original season from the database
        self.season.refresh_from_db()
        # Check that the original season is no longer active
        self.assertFalse(self.season.is_active)
        # Check that the new season is active
        self.assertTrue(new_season.is_active)

    def test_level_uniqueness(self):
        """Test that level names must be unique within a season."""
        # Attempt to create a duplicate level name
        with self.assertRaises(IntegrityError):
            Level.objects.create(season=self.season, name="A")

    def test_team_uniqueness(self):
        """Test that team names must be unique within a level."""
        # Attempt to create a duplicate team name
        with self.assertRaises(IntegrityError):
            Team.objects.create(level=self.level_a, name="Team A1")

    def test_active_season_helpers(self):
        """Test the helper methods for getting active season data."""
        # Test Level.get_active_season_levels()
        active_levels = Level.get_active_season_levels()
        self.assertEqual(active_levels.count(), 2)
        self.assertIn(self.level_a, active_levels)
        self.assertIn(self.level_b, active_levels)

        # Test Team.get_active_season_teams()
        active_teams = Team.get_active_season_teams()
        self.assertEqual(active_teams.count(), 4)
        self.assertIn(self.team_a1, active_teams)
        self.assertIn(self.team_a2, active_teams)
        self.assertIn(self.team_b1, active_teams)
        self.assertIn(self.team_b2, active_teams)

        # Create a second season (inactive)
        inactive_season = Season.objects.create(name="Inactive Season")
        inactive_level = Level.objects.create(season=inactive_season, name="C")
        Team.objects.create(level=inactive_level, name="Team C1")

        # Active season should still return only the active season's data
        self.assertEqual(Level.get_active_season_levels().count(), 2)
        self.assertEqual(Team.get_active_season_teams().count(), 4)

    def test_game_creation(self):
        """Test creating a game with valid and invalid data."""
        # Create a valid game
        game = Game.objects.create(
            level=self.level_a,
            week=1,
            team1=self.team_a1,
            team2=self.team_a2,
            referee_team=self.team_b1
        )
        self.assertEqual(game.level, self.level_a)
        self.assertEqual(game.team1, self.team_a1)
        self.assertEqual(game.team2, self.team_a2)
        self.assertEqual(game.referee_team, self.team_b1)

        # Test that a team cannot referee its own game (this is enforced at the application level, not DB)
        game_with_self_ref = Game.objects.create(
            level=self.level_a,
            week=2,
            team1=self.team_a1,
            team2=self.team_a2,
            referee_team=self.team_a1  # Same as team1
        )
        # This doesn't raise an error because it's an application-level rule, not DB constraint
        self.assertEqual(game_with_self_ref.referee_team, self.team_a1)
    
    def test_game_with_scores(self):
        """Test creating and querying games with scores."""
        # Create games with different score combinations
        game1 = Game.objects.create(
            level=self.level_a,
            week=1,
            team1=self.team_a1,
            team2=self.team_a2,
            referee_team=self.team_b1,
            team1_score=30,
            team2_score=25
        )
        
        game2 = Game.objects.create(
            level=self.level_a,
            week=2,
            team1=self.team_a1,
            team2=self.team_a2,
            referee_team=self.team_b1,
            team1_score=28,
            team2_score=28  # Tie
        )
        
        game3 = Game.objects.create(
            level=self.level_a,
            week=3,
            team1=self.team_a1,
            team2=self.team_a2,
            referee_team=self.team_b1
            # No scores set
        )
        
        # Verify scores are stored correctly
        self.assertEqual(game1.team1_score, 30)
        self.assertEqual(game1.team2_score, 25)
        self.assertEqual(game2.team1_score, 28)
        self.assertEqual(game2.team2_score, 28)
        self.assertIsNone(game3.team1_score)
        self.assertIsNone(game3.team2_score)


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
        config = get_config_from_schedule_creator(self.team_setup_output)
        
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
        
        config = get_config_from_schedule_creator(setup_with_offweek)
        
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
        
        # This should raise a ValueError
        with self.assertRaises(ValueError) as context:
            get_config_from_schedule_creator(uneven_setup)
        
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


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test season
        self.season = Season.objects.create(name="Test Season", is_active=True)
        # Create a level
        self.level = Level.objects.create(season=self.season, name="A")
        # Create teams
        self.team1 = Team.objects.create(level=self.level, name="Team A1")
        self.team2 = Team.objects.create(level=self.level, name="Team A2")
        self.team3 = Team.objects.create(level=self.level, name="Team A3")

    def test_season_list_view(self):
        """Test that the season list view loads correctly."""
        response = self.client.get(reverse('scheduler:season_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'scheduler/season_list.html')
        self.assertContains(response, "Test Season")

    def test_create_season_view(self):
        """Test that the create season view loads correctly."""
        response = self.client.get(reverse('scheduler:create_season'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'scheduler/create_season.html')

    def test_schedule_edit_view(self):
        """Test that the schedule edit view loads correctly."""
        # Create a game for the test season
        Game.objects.create(
            level=self.level,
            week=1,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3
        )
        
        response = self.client.get(reverse('scheduler:schedule_edit', args=[self.season.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'scheduler/schedule_edit.html')
        self.assertContains(response, "Test Season")
        self.assertContains(response, "Team A1")

    def test_get_season_schedule_data(self):
        """Test the API endpoint for getting season schedule data."""
        # Create a game
        game = Game.objects.create(
            level=self.level,
            week=1,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3
        )
        
        response = self.client.get(reverse('scheduler:get_season_schedule_data', args=[self.season.id]))
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertIn('games', data)
        self.assertEqual(len(data['games']), 1)
        
        # Check game data
        game_data = data['games'][0]
        self.assertEqual(game_data['id'], str(game.id))
        self.assertEqual(game_data['team1'], str(self.team1.id))
        self.assertEqual(game_data['team2'], str(self.team2.id))
        self.assertEqual(game_data['referee'], str(self.team3.id))

    def test_activate_season(self):
        """Test the activate season functionality."""
        # Create a second season (inactive)
        second_season = Season.objects.create(name="Second Season")
        
        # Activate the second season
        response = self.client.post(reverse('scheduler:activate_season', args=[second_season.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after successful activation
        
        # Refresh both season objects
        self.season.refresh_from_db()
        second_season.refresh_from_db()
        
        # Check that the statuses are updated
        self.assertFalse(self.season.is_active)
        self.assertTrue(second_season.is_active)

    def test_save_schedule_view(self):
        """Test the save schedule API endpoint."""
        # Prepare test data
        data = {
            'season_name': 'New Season',
            'setupData': {
                'teams': {
                    'A': ['Team X1', 'Team X2', 'Team X3'],
                    'B': ['Team Y1', 'Team Y2', 'Team Y3']
                }
            },
            'game_assignments': [
                {
                    'level': 'A',
                    'team1': 'Team X1', 
                    'team2': 'Team X2',
                    'referee': 'Team X3',
                    'week': 1,
                    'date': '2025-04-07',
                    'time': '18:10',
                    'court': 'Court 1'
                }
            ]
        }
        
        response = self.client.post(
            reverse('scheduler:save_schedule'),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the season was created
        self.assertTrue(Season.objects.filter(name='New Season').exists())
        new_season = Season.objects.get(name='New Season')
        
        # Check that levels and teams were created
        self.assertEqual(new_season.levels.count(), 2)
        self.assertEqual(Team.objects.filter(level__season=new_season).count(), 6)
        
        # Check that the game was created
        self.assertEqual(Game.objects.filter(level__season=new_season).count(), 1)
        
        # Test conflict with existing season name
        response = self.client.post(
            reverse('scheduler:save_schedule'),
            json.dumps(data),  # Same data with same season name
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 409)  # Conflict

    def test_update_schedule_view(self):
        """Test the update schedule API endpoint."""
        # Create a game for testing
        game = Game.objects.create(
            level=self.level,
            week=1,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3
        )
        
        # Prepare update data (creating a new game with different teams)
        update_data = {
            'games': [
                {
                    'level': str(self.level.id),
                    'team1': str(self.team1.id),
                    'team2': str(self.team3.id),  # Using team3 instead of team2
                    'referee': str(self.team2.id),  # Using team2 instead of team3 as referee
                    'week': '1',
                    'court': 'Court 2',  
                    'score1': '30',  
                    'score2': '25'   
                }
            ]
        }
        
        # The update_schedule endpoint deletes all games and creates new ones
        response = self.client.post(
            reverse('scheduler:update_schedule', args=[self.season.id]),
            json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that there's only one game now
        self.assertEqual(Game.objects.filter(level__season=self.season).count(), 1)
        
        # Verify the new game has the correct attributes
        new_game = Game.objects.get(level__season=self.season)
        self.assertEqual(new_game.team1, self.team1)
        self.assertEqual(new_game.team2, self.team3)  # Should be team3
        self.assertEqual(new_game.referee_team, self.team2)  # Should be team2
        self.assertEqual(new_game.court, 'Court 2')
        self.assertEqual(new_game.team1_score, 30)
        self.assertEqual(new_game.team2_score, 25)

    def test_validate_schedule_view(self):
        """Test the validate schedule API endpoint."""
        # Create a valid schedule for validation
        # This is a complete round-robin for 3 teams with each team playing twice
        valid_schedule = [
            {
                "week": 1,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["Team A1", "Team A2"],
                            "ref": "Team A3"
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
                            "teams": ["Team A1", "Team A3"],
                            "ref": "Team A2"
                        }
                    ]
                }
            },
            {
                "week": 3,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["Team A2", "Team A3"],
                            "ref": "Team A1"
                        }
                    ]
                }
            },
            # Add a second round-robin to satisfy validation
            {
                "week": 4,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["Team A1", "Team A2"],
                            "ref": "Team A3"
                        }
                    ]
                }
            },
            {
                "week": 5,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["Team A1", "Team A3"],
                            "ref": "Team A2"
                        }
                    ]
                }
            },
            {
                "week": 6,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["Team A2", "Team A3"],
                            "ref": "Team A1"
                        }
                    ]
                }
            }
        ]
        
        # Test data with the valid schedule
        data = {
            'schedule': valid_schedule,
            'config': {
                'levels': ['A'],
                'teams_per_level': {'A': 3}
            }
        }
        
        response = self.client.post(
            reverse('scheduler:validate_schedule'),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        
        # Check at least referee test passed
        self.assertTrue(result['Referee-Player']['passed'])

    def test_validation_with_errors(self):
        """Test the validation endpoint with an invalid schedule."""
        # Create an invalid schedule (referee playing in the same game)
        invalid_schedule = [
            {
                "week": 1,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["Team A1", "Team A2"],
                            "ref": "Team A1"  # A1 is both playing and refereeing
                        }
                    ]
                }
            }
        ]
        
        # Test data with the invalid schedule
        data = {
            'schedule': invalid_schedule,
            'config': {
                'levels': ['A'],
                'teams_per_level': {'A': 3}
            }
        }
        
        response = self.client.post(
            reverse('scheduler:validate_schedule'),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        
        # Check that the referee-player test failed
        self.assertFalse(result['Referee-Player']['passed'])
        # Verify the error message contains information about the conflict
        self.assertTrue(any("Referee Team A1 is playing in game" in error for error in result['Referee-Player']['errors']))


class EdgeCaseTests(TestCase):
    def setUp(self):
        # Create test data
        self.season = Season.objects.create(name="Edge Case Season", is_active=True)
        self.level = Level.objects.create(season=self.season, name="X")
        
        # Create exactly 3 teams for minimal round-robin
        self.teams = []
        for i in range(3):
            team = Team.objects.create(level=self.level, name=f"Team X{i+1}")
            self.teams.append(team)
    
    def test_single_week_schedule(self):
        """Test a minimal schedule with only one week."""
        # Create one week of games (minimal valid schedule)
        Game.objects.create(
            level=self.level,
            week=1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=self.teams[2],
            date_time=timezone.now()
        )
        
        # Retrieve and verify
        games = Game.objects.filter(level__season=self.season)
        self.assertEqual(games.count(), 1)
        
        # Test API response
        response = self.client.get(reverse('scheduler:get_season_schedule_data', args=[self.season.id]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['games']), 1)

    def test_game_with_future_date(self):
        """Test creating and retrieving games with future dates."""
        # Create a game with a future date
        future_date = timezone.now() + timedelta(days=30)
        game = Game.objects.create(
            level=self.level,
            week=1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=self.teams[2],
            date_time=future_date
        )
        
        # Verify the date was saved correctly
        retrieved_game = Game.objects.get(pk=game.pk)
        # Check that dates are within 1 second (to handle potential microsecond differences)
        self.assertAlmostEqual(
            retrieved_game.date_time.timestamp(),
            future_date.timestamp(),
            delta=1
        )

    def test_missing_referee(self):
        """Test schedule with games that have no referee assigned."""
        # Create a game without a referee
        game = Game.objects.create(
            level=self.level,
            week=1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=None  # No referee
        )
        
        # Verify the game was created correctly
        self.assertIsNone(game.referee_team)
        
        # Test API response handling of null referee
        response = self.client.get(reverse('scheduler:get_season_schedule_data', args=[self.season.id]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        game_data = data['games'][0]
        self.assertEqual(game_data['referee'], "")  # Empty string for null referee

    def test_same_team_twice_different_weeks(self):
        """Test a team playing against itself in different weeks (which should be allowed)."""
        # Create games with the same team1 and team2 in different weeks
        game1 = Game.objects.create(
            level=self.level,
            week=1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=self.teams[2]
        )
        
        game2 = Game.objects.create(
            level=self.level,
            week=2,
            team1=self.teams[0],
            team2=self.teams[1],  # Same matchup
            referee_team=self.teams[2]
        )
        
        # Both games should exist
        self.assertEqual(Game.objects.filter(level=self.level).count(), 2)

    def test_deleting_team_with_games(self):
        """Test what happens when deleting a team that has games."""
        # Create a game
        game = Game.objects.create(
            level=self.level,
            week=1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=self.teams[2]
        )
        
        # Try to delete team1 (should fail due to PROTECT constraint)
        with self.assertRaises(IntegrityError):
            self.teams[0].delete()
        
        # Verify the game still exists
        self.assertTrue(Game.objects.filter(pk=game.pk).exists())
        
        # Now try to delete the referee (should set referee to NULL due to SET_NULL)
        self.teams[2].delete()
        
        # Verify the game still exists but referee is NULL
        game.refresh_from_db()
        self.assertIsNone(game.referee_team)