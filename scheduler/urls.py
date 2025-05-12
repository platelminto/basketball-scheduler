from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # Renamed and updated view/name for listing seasons
    path("", views.season_list, name="season_list"),
    path("create/", views.create_season, name="create_season"),
    path("team_setup/", views.team_setup, name="team_setup"),
    path("game_assignment/", views.game_assignment, name="game_assignment"),
    path("validate_schedule/", views.validate_schedule, name="validate_schedule"),
    path(
        "auto_generate_schedule/",
        views.auto_generate_schedule,
        name="auto_generate_schedule",
    ),
    path("save_schedule/", views.save_schedule, name="save_schedule"),
    path(
        "season/<int:season_id>/activate/",
        views.activate_season,
        name="activate_season",
    ),
    # Add placeholder URL for editing season structure
    path(
        "season/<int:season_id>/edit_structure/",
        views.edit_season_structure,
        name="edit_season_structure",
    ),
    # URL for editing a specific schedule (games/scores)
    path(
        "season/<int:season_id>/edit_schedule/",
        views.schedule_edit,
        name="schedule_edit",
    ),
    # React version of the schedule edit page
    path(
        "season/<int:season_id>/edit_schedule/react/",
        views.schedule_edit_react,
        name="schedule_edit_react",
    ),
    # Data endpoint URL needs updating to match structure if desired, but keeping for now
    path(
        "schedule/<int:season_id>/data/",
        views.get_season_schedule_data,
        name="get_season_schedule_data",
    ),
    # Update endpoint URL needs updating to match structure if desired, but keeping for now
    path(
        "schedule/<int:season_id>/update/",
        views.update_schedule,
        name="update_schedule",
    ),

    # API endpoints for React - the full URL will be /scheduler/api/schedule/<season_id>/
    path("api/schedule/<int:season_id>/", views.schedule_data, name="schedule_data"),
]
