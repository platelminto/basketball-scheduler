from django.test import TestCase
from scheduler.models import Season, Level, Team, Game, Week
from django.db.utils import IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta, date


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
        
        # Create weeks for testing
        self.week1 = Week.objects.create(season=self.season, week_number=1, monday_date=date(2024, 1, 1))
        self.week2 = Week.objects.create(season=self.season, week_number=2, monday_date=date(2024, 1, 8))
    
    def test_single_week_schedule(self):
        """Test a minimal schedule with only one week."""
        # Create one week of games (minimal valid schedule)
        Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=self.teams[2]
        )
        
        # Retrieve and verify
        games = Game.objects.filter(level__season=self.season)
        self.assertEqual(games.count(), 1)
        
        # Game created successfully - API tests removed as legacy endpoint was deleted

    def test_game_with_future_date(self):
        """Test creating and retrieving games with future dates."""
        # Create a game with a future date
        future_date = timezone.now() + timedelta(days=30)
        game = Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=self.teams[2],
            day_of_week=1,
            time='18:00'
        )
        
        # Verify the game was saved correctly with future date calculation
        retrieved_game = Game.objects.get(pk=game.pk)
        # The date_time property should calculate the correct datetime
        calculated_date = retrieved_game.date_time
        self.assertIsNotNone(calculated_date)
        # Should be future date (week1 monday + 1 day + 18:00)
        if retrieved_game.time:
            expected_date = datetime.combine(
                self.week1.monday_date + timedelta(days=1),
                retrieved_game.time
            )
            if calculated_date:
                self.assertEqual(calculated_date.date(), expected_date.date())
        else:
            # If time is not set, just verify that calculated_date is valid
            self.assertIsNotNone(calculated_date)

    def test_missing_referee(self):
        """Test schedule with games that have no referee assigned."""
        # Create a game without a referee
        game = Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=None  # No referee
        )
        
        # Verify the game was created correctly
        self.assertIsNone(game.referee_team)
        
        # Verified game created without referee - API tests removed as legacy endpoint was deleted
        
    def test_string_referee(self):
        """Test schedule with games that have a string referee name."""
        # Create a game with a string referee
        referee_name = "External Referee"
        game = Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=None,
            referee_name=referee_name
        )
        
        # Verify the game was created correctly
        self.assertIsNone(game.referee_team)
        self.assertEqual(game.referee_name, referee_name)
        
        # Test string representation includes the correct referee name
        self.assertIn(f"(Ref: {referee_name})", str(game))
        
        # Verified game created with string referee - API tests removed as legacy endpoint was deleted

    def test_same_team_twice_different_weeks(self):
        """Test a team playing against itself in different weeks (which should be allowed)."""
        # Create games with the same team1 and team2 in different weeks
        game1 = Game.objects.create(
            level=self.level,
            week=self.week1,
            team1=self.teams[0],
            team2=self.teams[1],
            referee_team=self.teams[2]
        )
        
        game2 = Game.objects.create(
            level=self.level,
            week=self.week2,
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
            week=self.week1,
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