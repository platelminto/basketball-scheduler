from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # Main schedule viewer page
    path("", views.schedule_viewer, name="schedule"),
    path("create/", views.create_schedule, name="create_schedule"),
    path("team_setup/", views.team_setup, name="team_setup"),
    path("game_assignment/", views.game_assignment, name="game_assignment"),
    path("validate_schedule/", views.validate_schedule, name="validate_schedule"),
    path(
        "auto_generate_schedule/",
        views.auto_generate_schedule,
        name="auto_generate_schedule",
    ),
    path("save_schedule/", views.save_schedule, name="save_schedule"),
    # Updated URL for editing a specific schedule to use the renamed view
    path("schedule/<int:season_id>/", views.schedule_edit, name="schedule_edit"),
    # Data endpoint URL remains the same
    path(
        "schedule/<int:season_id>/data/",
        views.get_season_schedule_data,
        name="get_season_schedule_data",
    ),
    # Update endpoint URL remains the same
    path(
        "schedule/<int:season_id>/update/",
        views.update_schedule,
        name="update_schedule",
    ),
]
