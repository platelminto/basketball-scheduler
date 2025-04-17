from django.db import models
from django.db.models import Q  # Import Q for complex lookups


class Season(models.Model):
    """Represents a single league season."""

    name = models.CharField(
        max_length=100, unique=True, help_text="e.g., 24/25 Season 1"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Designates this season as the currently active one (only one can be active).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}{' (Active)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        # If this season is being set to active, deactivate all others first
        if self.is_active:
            Season.objects.filter(is_active=True).exclude(pk=self.pk).update(
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


class Level(models.Model):
    """Represents a skill level or division within a season."""

    season = models.ForeignKey(Season, related_name="levels", on_delete=models.CASCADE)
    name = models.CharField(max_length=50, help_text="e.g., Mid, High, Top, etc.")

    class Meta:
        unique_together = (
            "season",
            "name",
        )  # Level names must be unique within a season

    def __str__(self):
        return f"{self.name}"

    @classmethod
    def get_active_season_levels(cls):
        """Helper method to get levels for the active season."""
        active_season = Season.objects.filter(is_active=True).first()
        if active_season:
            return cls.objects.filter(season=active_season)
        return cls.objects.none()  # Return an empty queryset if no active season


class Team(models.Model):
    """Represents a team within a specific level."""

    level = models.ForeignKey(Level, related_name="teams", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("level", "name")  # Team names must be unique within a level
        ordering = ["level", "name"]

    def __str__(self):
        return f"{self.name} ({self.level.name})"

    @classmethod
    def get_active_season_teams(cls):
        """Helper method to get teams for the active season."""
        active_season = Season.objects.filter(is_active=True).first()
        if active_season:
            return cls.objects.filter(level__season=active_season)
        return cls.objects.none()


class Game(models.Model):
    """Represents a single game scheduled within a season."""

    level = models.ForeignKey(Level, related_name="games", on_delete=models.CASCADE)
    week = models.PositiveIntegerField()

    # Team relationships
    team1 = models.ForeignKey(
        Team, related_name="games_as_team1", on_delete=models.PROTECT
    )
    team2 = models.ForeignKey(
        Team, related_name="games_as_team2", on_delete=models.PROTECT
    )

    referee_team = models.ForeignKey(
        Team,
        related_name="games_as_referee",
        on_delete=models.SET_NULL,  # Changed from PROTECT
        null=True,  # Allow null in DB
        blank=True,  # Allow blank in forms/admin
    )
    
    # Allow for external referees (non-team referees)
    referee_name = models.CharField(max_length=100, null=True, blank=True)

    date_time = models.DateTimeField(null=True, blank=True)
    court = models.CharField(max_length=100, null=True, blank=True)
    team1_score = models.PositiveIntegerField(null=True, blank=True)
    team2_score = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["week", "level"]

    def __str__(self):
        # Handle potential None value for referee (either team or name)
        if self.referee_team:
            ref_name = self.referee_team.name
        elif self.referee_name:
            ref_name = self.referee_name
        else:
            ref_name = "N/A"
            
        return f"Week {self.week}: {self.level.name}: {self.team1.name} vs {self.team2.name} (Ref: {ref_name})"

    @classmethod
    def get_active_season_games(cls):
        """Helper method to get games for the active season."""
        active_season = Season.objects.filter(is_active=True).first()
        if active_season:
            return cls.objects.filter(level__season=active_season)
        return cls.objects.none()
