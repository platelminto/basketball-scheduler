from django.test import TestCase, Client, RequestFactory
from scheduler.models import Season, Level, Team, Game, Week, OffWeek
import json
from datetime import date


class UnifiedScheduleTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test season with existing data for update tests
        self.season = Season.objects.create(name="Existing Season", is_active=True)
        self.level = Level.objects.create(season=self.season, name="A")
        self.team1 = Team.objects.create(level=self.level, name="Team A1")
        self.team2 = Team.objects.create(level=self.level, name="Team A2")
        self.team3 = Team.objects.create(level=self.level, name="Team A3")
        
        # Create a week for update tests
        self.week = Week.objects.create(season=self.season, week_number=1, monday_date=date(2024, 1, 1))

    def test_unified_function_create_mode(self):
        """Test save_or_update_schedule in create mode."""
        data = {
            'season_name': 'Unified Create Season',
            'setupData': {
                'teams': {
                    'Level A': ['Team 1', 'Team 2', 'Team 3']
                },
                'schedule': {
                    'weeks': [
                        {'isOffWeek': False, 'weekStartDate': '2024-01-01'},
                        {'isOffWeek': True, 'weekStartDate': '2024-01-08'},
                        {'isOffWeek': False, 'weekStartDate': '2024-01-15'}
                    ]
                }
            },
            'week_dates': [
                {
                    'week_number': 1,
                    'monday_date': '2024-01-01',
                    'is_off_week': False
                },
                {
                    'week_number': 2,
                    'monday_date': '2024-01-08',
                    'is_off_week': True
                },
                {
                    'week_number': 3,
                    'monday_date': '2024-01-15',
                    'is_off_week': False
                }
            ],
            'game_assignments': [
                {
                    'level': 'Level A',
                    'team1': 'Team 1',
                    'team2': 'Team 2',
                    'referee': 'Team 3',
                    'week': 1,
                    'dayOfWeek': '1',
                    'time': '19:00',
                    'court': 'Court 1'
                },
                {
                    'level': 'Level A',
                    'team1': 'Team 1',
                    'team2': 'Team 3',
                    'referee': 'External Ref',
                    'week': 3,
                    'dayOfWeek': '2',
                    'time': '20:00',
                    'court': 'Court 2'
                }
            ]
        }

        from scheduler.views import save_or_update_schedule
        
        factory = RequestFactory()
        request = factory.post('/test/', json.dumps(data), content_type='application/json')
        response = save_or_update_schedule(request, season_id=None)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['games_created'], 2)
        self.assertIn('season_id', response_data)
        
        # Verify season was created
        season = Season.objects.get(name='Unified Create Season')
        self.assertEqual(season.levels.count(), 1)
        self.assertEqual(Team.objects.filter(level__season=season).count(), 3)
        self.assertEqual(Game.objects.filter(level__season=season).count(), 2)
        
        # Verify off-week was created
        self.assertEqual(OffWeek.objects.filter(season=season).count(), 1)

    def test_unified_function_update_mode(self):
        """Test save_or_update_schedule in update mode."""
        # Create an existing game to be replaced
        existing_game = Game.objects.create(
            level=self.level,
            week=self.week,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3,
            day_of_week=1,
            time='18:00',
            court='Old Court'
        )
        
        data = {
            'games': [
                {
                    'week': 1,
                    'level': self.level.id,
                    'team1': self.team1.id,
                    'team2': self.team2.id,
                    'referee': f'name:Updated External Ref',
                    'day': 2,
                    'time': '19:30',
                    'court': 'Updated Court',
                    'score1': '10',
                    'score2': '8'
                },
                {
                    'week': 1,
                    'level': self.level.id,
                    'team1': self.team2.id,
                    'team2': self.team3.id,
                    'referee': str(self.team1.id),
                    'day': 3,
                    'time': '20:00',
                    'court': 'Court 2'
                }
            ],
            'week_dates': [
                {
                    'id': self.week.id,
                    'date': '2024-02-01'
                }
            ]
        }

        from scheduler.views import save_or_update_schedule
        
        factory = RequestFactory()
        request = factory.post('/test/', json.dumps(data), content_type='application/json')
        response = save_or_update_schedule(request, season_id=self.season.id)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['games_created'], 2)
        self.assertEqual(response_data['deleted_count'], 1)
        
        # Verify old game was deleted and new games created
        self.assertFalse(Game.objects.filter(id=existing_game.id).exists())
        self.assertEqual(Game.objects.filter(level__season=self.season).count(), 2)
        
        # Verify week date was updated (week was recreated, so look it up again)
        updated_week = Week.objects.get(season=self.season, week_number=1)
        self.assertEqual(str(updated_week.monday_date), '2024-02-01')
        
        # Verify game details
        games = Game.objects.filter(level__season=self.season).order_by('day_of_week')
        self.assertEqual(games[0].referee_name, 'Updated External Ref')
        self.assertEqual(games[0].team1_score, 10)
        self.assertEqual(games[0].team2_score, 8)
        self.assertEqual(games[1].referee_team, self.team1)

    def test_unified_function_create_mode_conflict(self):
        """Test save_or_update_schedule create mode with existing season name."""
        data = {
            'season_name': 'Existing Season',  # Same as setUp season
            'setupData': {
                'teams': {'Level A': ['Team 1', 'Team 2']},
                'schedule': {'weeks': [{'isOffWeek': False, 'weekStartDate': '2024-01-01'}]}
            },
            'game_assignments': []
        }

        from scheduler.views import save_or_update_schedule
        
        factory = RequestFactory()
        request = factory.post('/test/', json.dumps(data), content_type='application/json')
        response = save_or_update_schedule(request, season_id=None)
        
        self.assertEqual(response.status_code, 409)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('already exists', response_data['message'])

    def test_unified_function_validation_errors(self):
        """Test save_or_update_schedule with validation errors."""
        data = {
            'season_name': 'Error Test Season',
            'setupData': {
                'teams': {'Level A': ['Team 1', 'Team 2']},
                'schedule': {'weeks': [{'isOffWeek': False, 'weekStartDate': '2024-01-01'}]}
            },
            'week_dates': [
                {
                    'week_number': 1,
                    'monday_date': '2024-01-01',
                    'is_off_week': False
                }
            ],
            'game_assignments': [
                {
                    'level': 'Level A',
                    'team1': 'Team 1',
                    'team2': 'Team 1',  # Same team - should cause error
                    'week': 1,
                    'dayOfWeek': '1',
                    'time': '19:00',
                    'court': 'Court 1'
                }
            ]
        }

        from scheduler.views import save_or_update_schedule
        
        factory = RequestFactory()
        request = factory.post('/test/', json.dumps(data), content_type='application/json')
        response = save_or_update_schedule(request, season_id=None)  # Don't skip validation for this test
        
        self.assertEqual(response.status_code, 200)  # Validation no longer blocks save
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        
        # Verify season was created successfully (validation doesn't block anymore)
        self.assertTrue(Season.objects.filter(name='Error Test Season').exists())

    def test_unified_function_missing_data(self):
        """Test save_or_update_schedule with missing required data."""
        # Test create mode missing data
        from scheduler.views import save_or_update_schedule
        
        factory = RequestFactory()
        
        # Missing setupData
        data = {'season_name': 'Test', 'game_assignments': []}
        request = factory.post('/test/', json.dumps(data), content_type='application/json')
        response = save_or_update_schedule(request, season_id=None)
        self.assertEqual(response.status_code, 400)
        
        # Test update mode missing data
        data = {}  # Missing games
        request = factory.post('/test/', json.dumps(data), content_type='application/json')
        response = save_or_update_schedule(request, season_id=self.season.id)
        self.assertEqual(response.status_code, 400)