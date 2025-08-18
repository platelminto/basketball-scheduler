from django.test import TestCase
from scheduler.models import Season, Level, TeamOrganization, SeasonTeam, Game, Week, OffWeek
from django.db.utils import IntegrityError
from datetime import date


class ModelTests(TestCase):
    def setUp(self):
        # Create a test season
        self.season = Season.objects.create(name="Test Season", is_active=True)
        # Create levels
        self.level_a = Level.objects.create(season=self.season, name="A")
        self.level_b = Level.objects.create(season=self.season, name="B")
        
        # Create team organizations
        self.team_org_a1 = TeamOrganization.objects.create(name="Team A1")
        self.team_org_a2 = TeamOrganization.objects.create(name="Team A2")
        self.team_org_b1 = TeamOrganization.objects.create(name="Team B1")
        self.team_org_b2 = TeamOrganization.objects.create(name="Team B2")
        
        # Create season teams
        self.season_team_a1 = SeasonTeam.objects.create(
            season=self.season, team=self.team_org_a1, level=self.level_a
        )
        self.season_team_a2 = SeasonTeam.objects.create(
            season=self.season, team=self.team_org_a2, level=self.level_a
        )
        self.season_team_b1 = SeasonTeam.objects.create(
            season=self.season, team=self.team_org_b1, level=self.level_b
        )
        self.season_team_b2 = SeasonTeam.objects.create(
            season=self.season, team=self.team_org_b2, level=self.level_b
        )
        
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
        # The new season should be active
        self.assertTrue(new_season.is_active)

    def test_level_name_unique_per_season(self):
        """Test that level names are unique within a season."""
        # This should work - different season
        new_season = Season.objects.create(name="Another Season")
        Level.objects.create(season=new_season, name="A")
        
        # This should fail - same name within same season
        with self.assertRaises(IntegrityError):
            Level.objects.create(season=self.season, name="A")

    def test_week_number_unique_per_season(self):
        """Test that week numbers are unique within a season."""
        # This should work - different season
        new_season = Season.objects.create(name="Another Season")
        Week.objects.create(season=new_season, week_number=1, monday_date=date(2024, 2, 1))
        
        # This should fail - same week number within same season
        with self.assertRaises(IntegrityError):
            Week.objects.create(season=self.season, week_number=1, monday_date=date(2024, 2, 1))

    def test_offweek_date_unique_per_season(self):
        """Test that off-week dates are unique within a season."""
        offweek_date = date(2024, 1, 22)
        OffWeek.objects.create(season=self.season, monday_date=offweek_date)
        
        # This should work - different season
        new_season = Season.objects.create(name="Another Season")
        OffWeek.objects.create(season=new_season, monday_date=offweek_date)
        
        # This should fail - same date within same season
        with self.assertRaises(IntegrityError):
            OffWeek.objects.create(season=self.season, monday_date=offweek_date)

    def test_team_organization_participation_unique_per_season(self):
        """Test that a team organization can only participate once per season."""
        # This should fail - team already participating in this season
        with self.assertRaises(IntegrityError):
            SeasonTeam.objects.create(
                season=self.season, team=self.team_org_a1, level=self.level_b
            )

    def test_game_creation(self):
        """Test creating a game with valid and invalid data."""
        # Create a valid game
        game = Game.objects.create(
            level=self.level_a,
            week=self.week1,
            season_team1=self.season_team_a1,
            season_team2=self.season_team_a2,
            referee_season_team=self.season_team_b1
        )
        self.assertEqual(game.level, self.level_a)
        self.assertEqual(game.season_team1, self.season_team_a1)
        self.assertEqual(game.season_team2, self.season_team_a2)
        self.assertEqual(game.referee_season_team, self.season_team_b1)

        # Test that a team cannot referee its own game (this is enforced at the application level, not DB)
        game_with_self_ref = Game.objects.create(
            level=self.level_a,
            week=self.week2,
            season_team1=self.season_team_a1,
            season_team2=self.season_team_a2,
            referee_season_team=self.season_team_a1  # Same as team1
        )
        # This doesn't raise an error because it's an application-level rule, not DB constraint
        self.assertEqual(game_with_self_ref.referee_season_team, self.season_team_a1)
    
    def test_game_with_scores(self):
        """Test creating and querying games with scores."""
        # Create games with different score combinations
        game1 = Game.objects.create(
            level=self.level_a,
            week=self.week1,
            season_team1=self.season_team_a1,
            season_team2=self.season_team_a2,
            team1_score=85,
            team2_score=78
        )
        
        game2 = Game.objects.create(
            level=self.level_a,
            week=self.week2,
            season_team1=self.season_team_a1,
            season_team2=self.season_team_a2,
            team1_score=None,  # Game not completed
            team2_score=None
        )
        
        # Test that we can query for completed games
        completed_games = Game.objects.filter(
            team1_score__isnull=False, 
            team2_score__isnull=False
        )
        self.assertEqual(completed_games.count(), 1)
        self.assertEqual(completed_games.first(), game1)
        
        # Test that we can query for incomplete games
        incomplete_games = Game.objects.filter(
            team1_score__isnull=True, 
            team2_score__isnull=True
        )
        self.assertEqual(incomplete_games.count(), 1)
        self.assertEqual(incomplete_games.first(), game2)

    def test_game_helper_methods(self):
        """Test the helper methods on Game model."""
        game = Game.objects.create(
            level=self.level_a,
            week=self.week1,
            season_team1=self.season_team_a1,
            season_team2=self.season_team_a2,
            referee_season_team=self.season_team_b1,
            team1_score=85,
            team2_score=78
        )
        
        # Test team name helpers
        self.assertEqual(game.get_team1_name(), "Team A1")
        self.assertEqual(game.get_team2_name(), "Team A2")
        self.assertEqual(game.get_referee_name(), "Team B1")
        
        # Test with external referee
        game_external_ref = Game.objects.create(
            level=self.level_a,
            week=self.week2,
            season_team1=self.season_team_a1,
            season_team2=self.season_team_a2,
            referee_name="External Ref"
        )
        self.assertEqual(game_external_ref.get_referee_name(), "External Ref")

    def test_model_string_representations(self):
        """Test the string representations of models."""
        self.assertEqual(str(self.season), "Test Season (Active)")
        self.assertEqual(str(self.level_a), "A")
        self.assertEqual(str(self.team_org_a1), "Team A1")
        self.assertEqual(str(self.season_team_a1), "Team A1 in A (Test Season)")
        self.assertEqual(str(self.week1), "1")
        
        # Test off-week string representation
        off_week = OffWeek.objects.create(
            season=self.season,
            monday_date=date(2024, 1, 22),
            title="Holiday Break",
            description="No games this week"
        )
        expected_str = "Holiday Break: 2024-01-22 - No games this week"
        self.assertEqual(str(off_week), expected_str)