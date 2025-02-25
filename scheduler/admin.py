from django.contrib import admin
from .models import Level, Team, Game


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "level",
        "wins",
        "losses",
        "ties",
        "points_for",
        "points_against",
        "point_differential",
    )
    list_filter = ("level",)
    search_fields = ("name",)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "week",
        "level",
        "team1",
        "team2",
        "referee",
        "start_time",
        "team1_score",
        "team2_score",
        "is_played",
    )
    list_filter = ("week", "level", "is_played")
    search_fields = ("team1__name", "team2__name", "referee__name")
    raw_id_fields = ("team1", "team2", "referee")
