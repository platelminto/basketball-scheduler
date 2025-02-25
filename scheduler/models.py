from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q


class Level(models.Model):
    """Represents a competition level (Mid, High, Top)"""

    LEVEL_CHOICES = [
        ("MID", "Mid"),
        ("HIGH", "High"),
        ("TOP", "Top"),
    ]

    name = models.CharField(max_length=4, choices=LEVEL_CHOICES, unique=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    """Represents a team in the league"""

    name = models.CharField(max_length=100)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="teams")

    # Stats fields (these could be calculated dynamically, but storing them allows for easier querying)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    ties = models.PositiveIntegerField(default=0)
    points_for = models.PositiveIntegerField(default=0)
    points_against = models.PositiveIntegerField(default=0)

    @property
    def games_played(self):
        return self.wins + self.losses + self.ties

    @property
    def point_differential(self):
        return self.points_for - self.points_against

    def __str__(self):
        return f"{self.name} ({self.level})"

    class Meta:
        constraints = [
            # Ensure team names are unique within a level
            models.UniqueConstraint(
                fields=["name", "level"], name="unique_team_per_level"
            )
        ]


class Game(models.Model):
    """Represents a game between two teams"""

    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_games")
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_games")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="games")
    referee = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="refereed_games"
    )
    start_time = models.TimeField()
    week = models.PositiveSmallIntegerField()

    # Scores (null until the game is played)
    team1_score = models.PositiveIntegerField(null=True, blank=True)
    team2_score = models.PositiveIntegerField(null=True, blank=True)

    # Convert property to a field for admin display
    is_played = models.BooleanField(default=False, editable=False)

    # Add this new field
    schedule = models.ForeignKey(
        "SavedSchedule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="games",
    )

    @property
    def winner(self):
        if not self.is_played:
            return None
        if self.team1_score is not None and self.team2_score is not None:
            if self.team1_score > self.team2_score:
                return self.team1
            elif self.team2_score > self.team1_score:
                return self.team2
        return None  # Tie or not played

    def clean(self):
        # Ensure team1 and team2 are different
        if self.team1 == self.team2:
            raise ValidationError("A team cannot play against itself")

        # Ensure teams and referee are from the same level
        if (
            self.team1.level != self.level
            or self.team2.level != self.level
            or self.referee.level != self.level
        ):
            raise ValidationError("Teams and referee must be from the same level")

        # Ensure referee is not one of the playing teams
        if self.referee == self.team1 or self.referee == self.team2:
            raise ValidationError("Referee cannot be one of the playing teams")

        # Check if game is played
        self.is_played = self.team1_score is not None and self.team2_score is not None

    def save(self, *args, **kwargs):
        # Get the old instance if this is an update
        old_game = None
        if self.pk:
            old_game = Game.objects.filter(pk=self.pk).first()

        self.clean()

        # Set the level automatically based on team1's level
        self.level = self.team1.level

        # Call the original save method
        super().save(*args, **kwargs)

        # Update team stats if game is played
        if self.is_played:
            self.update_team_stats(old_game)

    def update_team_stats(self, old_game=None):
        # Reset previous stats for the teams if this is updating an existing game
        if old_game and old_game.is_played:
            # Revert old stats
            if old_game.team1_score > old_game.team2_score:
                old_game.team1.wins -= 1
                old_game.team2.losses -= 1
            elif old_game.team2_score > old_game.team1_score:
                old_game.team2.wins -= 1
                old_game.team1.losses -= 1
            else:
                old_game.team1.ties -= 1
                old_game.team2.ties -= 1

            old_game.team1.points_for -= old_game.team1_score
            old_game.team1.points_against -= old_game.team2_score
            old_game.team2.points_for -= old_game.team2_score
            old_game.team2.points_against -= old_game.team1_score

            old_game.team1.save()
            old_game.team2.save()

        # Update new stats - ensure scores are not None
        if self.team1_score is not None and self.team2_score is not None:
            if self.team1_score > self.team2_score:
                self.team1.wins += 1
                self.team2.losses += 1
            elif self.team2_score > self.team1_score:
                self.team2.wins += 1
                self.team1.losses += 1
            else:
                self.team1.ties += 1
                self.team2.ties += 1

            self.team1.points_for += self.team1_score
            self.team1.points_against += self.team2_score
            self.team2.points_for += self.team2_score
            self.team2.points_against += self.team1_score

            self.team1.save()
            self.team2.save()

    def __str__(self):
        result = f"Week {self.week}: {self.team1} vs {self.team2} (Ref: {self.referee}, Time: {self.start_time.strftime('%H:%M')})"
        if self.is_played:
            result += f" - Score: {self.team1_score}-{self.team2_score}"
        return result


class SavedSchedule(models.Model):
    """Represents a saved schedule configuration"""

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Raw schedule data from the generator
    raw_schedule_data = models.JSONField()

    # Complete schedule data including dates, times, off-weeks
    complete_schedule_data = models.JSONField(null=True, blank=True)

    # Start date for the schedule
    start_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%d/%m/%Y')})"
