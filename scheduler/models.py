from datetime import datetime, timedelta
from django.db import models
from django.db.models import Q  # Import Q for complex lookups


class SeasonManager(models.Manager):
    """Custom manager that filters out deleted seasons by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Season(models.Model):
    """Represents a single league season."""

    name = models.CharField(
        max_length=100, unique=True, help_text="e.g., 24/25 Season 1"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Designates this season as the currently active one (only one can be active).",
    )
    slot_duration_minutes = models.PositiveIntegerField(
        default=70,
        help_text="Duration of each game slot in minutes (includes game time + halftime)"
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text="Marks this season as soft-deleted (hidden from normal queries)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Managers
    objects = SeasonManager()  # Default manager excludes deleted seasons
    all_objects = models.Manager()  # Manager that includes deleted seasons

    def __str__(self):
        return f"{self.name}{' (Active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        # Prevent deleted seasons from being made active
        if self.is_deleted and self.is_active:
            raise ValueError("Deleted seasons cannot be made active")
        
        # If this season is being set to active, deactivate all others first
        if self.is_active:
            Season.all_objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
        super().save(*args, **kwargs)

    class Meta:
        # Optional: Add a constraint to double-ensure uniqueness at the DB level,
        # though the save method handles the logic application-side.
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="unique_active_season",
            )
        ]


class LevelManager(models.Manager):
    """Custom manager that filters out levels from deleted seasons by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(season__is_deleted=False)


class Level(models.Model):
    """Represents a skill level or division within a season."""

    season = models.ForeignKey(Season, related_name="levels", on_delete=models.CASCADE)
    name = models.CharField(max_length=50, help_text="e.g., Mid, High, Top, etc.")
    slot_duration_minutes = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Duration override for this level (falls back to season default if not set)"
    )
    
    # Managers
    objects = LevelManager()  # Default manager excludes levels from deleted seasons
    all_objects = models.Manager()  # Manager that includes levels from deleted seasons

    class Meta:
        unique_together = (
            "season",
            "name",
        )  # Level names must be unique within a season

    def __str__(self):
        return f"{self.name}"

    def get_effective_slot_duration(self):
        """Returns the slot duration for this level, falling back to season default"""
        return self.slot_duration_minutes if self.slot_duration_minutes is not None else self.season.slot_duration_minutes

    @classmethod
    def get_active_season_levels(cls):
        """Helper method to get levels for the active season."""
        active_season = Season.objects.filter(is_active=True).first()
        if active_season:
            return cls.objects.filter(season=active_season)
        return cls.objects.none()  # Return an empty queryset if no active season


class TeamOrganizationManager(models.Manager):
    """Custom manager that filters out deleted teams by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class TeamOrganization(models.Model):
    """Represents a team organization that exists independently of seasons."""
    
    name = models.CharField(
        max_length=100, 
        help_text="Team name that persists across seasons"
    )
    is_archived = models.BooleanField(
        default=False,
        help_text="Whether this team is archived and shouldn't appear in new season creation"
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text="Marks this team as soft-deleted (hidden from normal queries)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Managers
    objects = TeamOrganizationManager()  # Default manager excludes deleted teams
    all_objects = models.Manager()  # Manager that includes deleted teams
    
    class Meta:
        ordering = ["name"]
        
    def __str__(self):
        suffix = ""
        if self.is_deleted:
            suffix = " (Deleted)"
        elif self.is_archived:
            suffix = " (Archived)"
        return f"{self.name}{suffix}"
    
    @classmethod
    def get_active_teams(cls):
        """Get all non-archived, non-deleted teams."""
        return cls.objects.filter(is_archived=False)


class SeasonTeamManager(models.Manager):
    """Custom manager that filters out season teams from deleted seasons/teams by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(
            season__is_deleted=False,
            team__is_deleted=False
        )


class SeasonTeam(models.Model):
    """Junction model linking teams to seasons with level assignment."""
    
    season = models.ForeignKey(Season, related_name="season_teams", on_delete=models.CASCADE)
    team = models.ForeignKey(TeamOrganization, related_name="season_participations", on_delete=models.PROTECT)
    level = models.ForeignKey(Level, related_name="season_teams", on_delete=models.CASCADE)
    
    # Managers
    objects = SeasonTeamManager()  # Default manager excludes deleted seasons/teams
    all_objects = models.Manager()  # Manager that includes deleted seasons/teams
    
    class Meta:
        unique_together = ("season", "team")  # Team can only participate once per season
        ordering = ["level", "team__name"]
        
    def __str__(self):
        return f"{self.team.name} in {self.level.name} ({self.season.name})"
    
    @classmethod
    def get_active_season_teams(cls):
        """Helper method to get teams for the active season."""
        active_season = Season.objects.filter(is_active=True).first()
        if active_season:
            return cls.objects.filter(season=active_season)
        return cls.objects.none()




class WeekManager(models.Manager):
    """Custom manager that filters out weeks from deleted seasons by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(season__is_deleted=False)


class Week(models.Model):
    """Represents a week of games in a season."""

    season = models.ForeignKey(Season, related_name="weeks", on_delete=models.CASCADE)
    week_number = models.PositiveIntegerField()
    monday_date = models.DateField()
    
    # Managers
    objects = WeekManager()  # Default manager excludes weeks from deleted seasons
    all_objects = models.Manager()  # Manager that includes weeks from deleted seasons
    
    class Meta:
        unique_together = ("season", "week_number")
    
    def __str__(self):
        return f"{self.week_number}"


class OffWeekManager(models.Manager):
    """Custom manager that filters out off-weeks from deleted seasons by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(season__is_deleted=False)


class OffWeek(models.Model):
    """Represents an off week in a season."""

    season = models.ForeignKey(Season, related_name="off_weeks", on_delete=models.CASCADE)
    monday_date = models.DateField()
    title = models.CharField(
        max_length=100,
        default="Off Week",
        help_text="Title of this non-league week"
    )
    description = models.TextField(
        default="No games scheduled",
        help_text="Description of what's happening this week (e.g., 'Charity Tournament', 'Holiday Break')"
    )
    has_basketball = models.BooleanField(
        default=False,
        help_text="Whether basketball events are happening this week (affects styling)"
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Start time for events this week"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="End time for events this week"
    )
    
    # Managers
    objects = OffWeekManager()  # Default manager excludes off-weeks from deleted seasons
    all_objects = models.Manager()  # Manager that includes off-weeks from deleted seasons
    
    class Meta:
        unique_together = ("season", "monday_date")
    
    def __str__(self):
        return f"{self.title}: {self.monday_date} - {self.description}"


class GameManager(models.Manager):
    """Custom manager that filters out games from deleted seasons/teams by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(
            level__season__is_deleted=False,
            season_team1__season__is_deleted=False,
            season_team1__team__is_deleted=False,
            season_team2__season__is_deleted=False,
            season_team2__team__is_deleted=False
        )


class Game(models.Model):
    """Represents a single game scheduled within a season."""

    level = models.ForeignKey(Level, related_name="games", on_delete=models.CASCADE)
    week = models.ForeignKey(Week, related_name="games", on_delete=models.PROTECT)

    # Team relationships using SeasonTeam
    season_team1 = models.ForeignKey(
        'SeasonTeam', related_name="games_as_team1", on_delete=models.PROTECT
    )
    season_team2 = models.ForeignKey(
        'SeasonTeam', related_name="games_as_team2", on_delete=models.PROTECT
    )
    
    referee_season_team = models.ForeignKey(
        'SeasonTeam',
        related_name="games_as_referee",
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Allow for external referees (non-team referees)
    referee_name = models.CharField(max_length=100, null=True, blank=True)
    day_of_week = models.PositiveIntegerField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    court = models.CharField(max_length=100, null=True, blank=True)
    team1_score = models.PositiveIntegerField(null=True, blank=True)
    team2_score = models.PositiveIntegerField(null=True, blank=True)
    
    # Managers
    objects = GameManager()  # Default manager excludes games from deleted seasons/teams
    all_objects = models.Manager()  # Manager that includes games from deleted seasons/teams

    class Meta:
        ordering = ["week", "level"]

    def __str__(self):
        team1_name = self.season_team1.team.name if self.season_team1 else "Unknown"
        team2_name = self.season_team2.team.name if self.season_team2 else "Unknown"
        
        # Handle referee
        if self.referee_season_team:
            ref_name = self.referee_season_team.team.name
        elif self.referee_name:
            ref_name = self.referee_name
        else:
            ref_name = "N/A"
            
        return f"Week {self.week}: {self.level.name}: {team1_name} vs {team2_name} (Ref: {ref_name})"

    @classmethod
    def get_active_season_games(cls):
        """Helper method to get games for the active season."""
        active_season = Season.objects.filter(is_active=True).first()
        if active_season:
            return cls.objects.filter(level__season=active_season)
        return cls.objects.none()

    @property
    def date_time(self):
        if self.time and self.day_of_week is not None:
            return datetime.combine(self.week.monday_date + timedelta(days=self.day_of_week), self.time)

        return None
    
    def get_team1_name(self):
        """Get team1 name."""
        return self.season_team1.team.name if self.season_team1 else "Unknown"
    
    def get_team2_name(self):
        """Get team2 name."""
        return self.season_team2.team.name if self.season_team2 else "Unknown"
    
    def get_referee_name(self):
        """Get referee name."""
        if self.referee_season_team:
            return self.referee_season_team.team.name
        elif self.referee_name:
            return self.referee_name
        return "N/A"
