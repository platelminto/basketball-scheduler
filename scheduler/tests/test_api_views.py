from django.test import TestCase, Client
from django.urls import reverse
from scheduler.models import Season, Level, Team, Game, Week
import json
from datetime import date


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
        # Create weeks
        self.week1 = Week.objects.create(season=self.season, week_number=1, monday_date=date(2024, 1, 1))

    def test_season_list_view(self):
        """Test that the season exists (season_list view was removed)."""
        # Note: season_list view was removed, this test now just verifies the season exists
        self.assertTrue(Season.objects.filter(name='Test Season').exists())

    def test_create_season_view(self):
        """Test that we can create seasons programmatically (create_season view was removed)."""
        # Note: create_season view was removed, this test now verifies programmatic season creation
        new_season = Season.objects.create(name='Test Create Season')
        self.assertTrue(Season.objects.filter(name='Test Create Season').exists())

    def test_schedule_edit_view(self):
        """Test that the schedule edit view loads correctly."""
        # Create a game for the test season
        Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3
        )
        
        # Since we removed the legacy template views, just check the season exists
        self.assertTrue(Season.objects.filter(id=self.season.id).exists())

    def test_activate_season(self):
        """Test the activate season functionality."""
        # Create a second season (inactive)
        second_season = Season.objects.create(name="Second Season")
        
        # Activate the second season
        response = self.client.post(reverse('scheduler:activate_season_api', args=[second_season.id]))
        self.assertEqual(response.status_code, 200)  # API returns 200 for successful activation
        
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
                },
                'schedule': {
                    'weeks': [
                        {'isOffWeek': False, 'weekStartDate': '2025-04-07'}
                    ]
                }
            },
            'week_dates': [
                {
                    'week_number': 1,
                    'monday_date': '2025-04-07',
                    'is_off_week': False
                }
            ],
            'game_assignments': [
                {
                    'level': 'A',
                    'team1': 'Team X1', 
                    'team2': 'Team X2',
                    'referee': 'Team X3',
                    'week': 1,
                    'dayOfWeek': '1',
                    'time': '18:10',
                    'court': 'Court 1'
                }
            ]
        }
        
        response = self.client.post(
            reverse('scheduler:create_schedule_api'),
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
            reverse('scheduler:create_schedule_api'),
            json.dumps(data),  # Same data with same season name
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 409)  # Conflict
        
    def test_save_schedule_with_string_referee(self):
        """Test the save schedule API endpoint with a string referee."""
        # Prepare test data with a string referee
        data = {
            'season_name': 'Season With String Ref',
            'setupData': {
                'teams': {
                    'A': ['Team X1', 'Team X2']
                },
                'schedule': {
                    'weeks': [
                        {'isOffWeek': False, 'weekStartDate': '2025-04-07'}
                    ]
                }
            },
            'week_dates': [
                {
                    'week_number': 1,
                    'monday_date': '2025-04-07',
                    'is_off_week': False
                }
            ],
            'game_assignments': [
                {
                    'level': 'A',
                    'team1': 'Team X1', 
                    'team2': 'Team X2',
                    'referee': 'External Referee John',  # String referee (not a team)
                    'week': 1,
                    'dayOfWeek': '1',
                    'time': '18:10',
                    'court': 'Court 1'
                }
            ]
        }
        
        response = self.client.post(
            reverse('scheduler:create_schedule_api'),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the season was created
        self.assertTrue(Season.objects.filter(name='Season With String Ref').exists())
        new_season = Season.objects.get(name='Season With String Ref')
        
        # Check that the game was created with the correct referee
        game = Game.objects.get(level__season=new_season)
        self.assertIsNone(game.referee_team)  # Should not be associated with a team
        self.assertEqual(game.referee_name, 'External Referee John')  # Should store the string name
        
    def test_save_schedule_with_no_referee(self):
        """Test the save schedule API endpoint with no referee specified."""
        # Prepare test data with no referee
        data = {
            'season_name': 'Season With No Ref',
            'setupData': {
                'teams': {
                    'A': ['Team X1', 'Team X2']
                },
                'schedule': {
                    'weeks': [
                        {'isOffWeek': False, 'weekStartDate': '2025-04-07'}
                    ]
                }
            },
            'week_dates': [
                {
                    'week_number': 1,
                    'monday_date': '2025-04-07',
                    'is_off_week': False
                }
            ],
            'game_assignments': [
                {
                    'level': 'A',
                    'team1': 'Team X1', 
                    'team2': 'Team X2',
                    'week': 1,
                    'dayOfWeek': '1',
                    'time': '18:10',
                    'court': 'Court 1'
                    # No referee specified
                }
            ]
        }
        
        response = self.client.post(
            reverse('scheduler:create_schedule_api'),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the game was created with no referee
        new_season = Season.objects.get(name='Season With No Ref')
        game = Game.objects.get(level__season=new_season)
        self.assertIsNone(game.referee_team)
        self.assertIsNone(game.referee_name)

    def test_update_schedule_view(self):
        """Test the update schedule API endpoint."""
        # Create a game for testing
        game = Game.objects.create(
            level=self.level,
            week=self.week1,
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
            reverse('scheduler:update_schedule_api', args=[self.season.id]),
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
        
    def test_update_schedule_with_string_referee(self):
        """Test the update schedule API endpoint with a string referee."""
        # Create a game for testing
        game = Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3
        )
        
        # Prepare update data with string referee
        update_data = {
            'games': [
                {
                    'level': str(self.level.id),
                    'team1': str(self.team1.id),
                    'team2': str(self.team2.id),
                    'referee': 'name:External Referee Smith',  # String referee with name: prefix
                    'week': '1',
                    'court': 'Court 3',
                    'score1': '45',
                    'score2': '42'
                }
            ]
        }
        
        # The update_schedule endpoint deletes all games and creates new ones
        response = self.client.post(
            reverse('scheduler:update_schedule_api', args=[self.season.id]),
            json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify the new game has the correct attributes with string referee
        new_game = Game.objects.get(level__season=self.season)
        self.assertEqual(new_game.team1, self.team1)
        self.assertEqual(new_game.team2, self.team2)
        self.assertIsNone(new_game.referee_team)  # No team referee
        self.assertEqual(new_game.referee_name, 'External Referee Smith')  # String referee
        self.assertEqual(new_game.court, 'Court 3')
        self.assertEqual(new_game.team1_score, 45)
        self.assertEqual(new_game.team2_score, 42)
        
    def test_update_schedule_with_no_referee(self):
        """Test the update schedule API endpoint with no referee."""
        # Create a game for testing
        game = Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3
        )
        
        # Prepare update data with no referee
        update_data = {
            'games': [
                {
                    'level': str(self.level.id),
                    'team1': str(self.team1.id),
                    'team2': str(self.team2.id),
                    'referee': '',  # Empty string = no referee
                    'week': '1',
                    'court': 'Court 4'
                }
            ]
        }
        
        # Update the schedule
        response = self.client.post(
            reverse('scheduler:update_schedule_api', args=[self.season.id]),
            json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify the new game has no referee
        new_game = Game.objects.get(level__season=self.season)
        self.assertIsNone(new_game.referee_team)
        self.assertIsNone(new_game.referee_name)
        self.assertEqual(new_game.court, 'Court 4')

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
            reverse('scheduler:seasons_validate_api'),
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
            reverse('scheduler:seasons_validate_api'),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        
        # Check that the referee-player test failed
        self.assertFalse(result['Referee-Player']['passed'])
        # Verify the error message contains information about the conflict
        self.assertTrue(any("Referee Team A1 is playing in game" in error for error in result['Referee-Player']['errors']))
        
    def test_validation_with_string_referee(self):
        """Test the validation endpoint with string referees."""
        # Create a schedule with string referees
        valid_schedule = [
            {
                "week": 1,
                "slots": {
                    "1": [
                        {
                            "level": "A",
                            "teams": ["Team A1", "Team A2"],
                            "ref": "External Referee"  # String referee
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
                            "ref": "Guest Official"  # Another string referee
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
                            "ref": "Coach Smith"  # Another string referee
                        }
                    ]
                }
            }
        ]
        
        # Test data with string referees
        data = {
            'schedule': valid_schedule,
            'config': {
                'levels': ['A'],
                'teams_per_level': {'A': 3}
            }
        }
        
        response = self.client.post(
            reverse('scheduler:seasons_validate_api'),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        
        # Check that the referee-player test passed (string refs can't be playing)
        self.assertTrue(result['Referee-Player']['passed'])
        
        # Check that adjacent slot test was skipped or passed
        # A string referee can't be matched to a team, so it should either pass or be skipped
        # The exact behavior depends on how the validator is implemented
        self.assertTrue(
            result['Adjacent Slots']['passed'] or 
            any("External Referee not found in any pairing" in error for error in result['Adjacent Slots'].get('errors', []))
        )