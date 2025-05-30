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
    # call save_or_update_schedule with skip_validation=True
    path(
        "save_or_update_schedule/",
        lambda request, *args, **kwargs: views.save_or_update_schedule(
            request, skip_validation=True, *args, **kwargs
        ),
        name="save_or_update_schedule",
    ),
    path(
        "save_or_update_schedule/<int:season_id>/",
        lambda request, season_id, *args, **kwargs: views.save_or_update_schedule(
            request, season_id=season_id, skip_validation=True, *args, **kwargs
        ),
        name="save_or_update_schedule_with_id",
    ),
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
    # API endpoints for React
    path("api/seasons/", views.seasons_api, name="seasons_api"),
    path(
        "api/seasons/<int:season_id>/activate/",
        views.activate_season_api,
        name="activate_season_api",
    ),
    path("api/schedule/<int:season_id>/", views.schedule_data, name="schedule_data"),
    # Routes for the unified React SPA
    path("app/", views.schedule_app, name="schedule_app"),
    # Catch all routes under app/ to be handled by the React Router
    path("app/<path:path>", views.schedule_app, name="schedule_app_paths"),
]
