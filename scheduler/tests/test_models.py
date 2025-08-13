from django.test import TestCase
from scheduler.models import Season, Level, Team, Game, Week, OffWeek
from django.db.utils import IntegrityError
from datetime import date


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
        # Create weeks
        self.week1 = Week.objects.create(season=self.season, week_number=1, monday_date=date(2024, 1, 1))
        self.week2 = Week.objects.create(season=self.season, week_number=2, monday_date=date(2024, 1, 8))
        self.week3 = Week.objects.create(season=self.season, week_number=3, monday_date=date(2024, 1, 15))

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
            week=self.week1,
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
            week=self.week2,
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
            week=self.week1,
            team1=self.team_a1,
            team2=self.team_a2,
            referee_team=self.team_b1,
            team1_score=30,
            team2_score=25
        )
        
        game2 = Game.objects.create(
            level=self.level_a,
            week=self.week2,
            team1=self.team_a1,
            team2=self.team_a2,
            referee_team=self.team_b1,
            team1_score=28,
            team2_score=28  # Tie
        )
        
        game3 = Game.objects.create(
            level=self.level_a,
            week=self.week3,
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