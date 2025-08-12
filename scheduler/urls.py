from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # Renamed and updated view/name for listing seasons
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
    path("api/seasons/", views.get_seasons, name="seasons_api"),
    path(
        "api/seasons/<int:season_id>/activate/",
        views.activate_season,
        name="activate_season_api",
    ),
    path("api/schedule/<int:season_id>/", views.schedule_data, name="schedule_data"),
    path("api/public/schedule/", views.public_schedule_data, name="public_schedule_data"),
    path("api/update_teams_levels/<int:season_id>/", views.update_teams_levels, name="update_teams_levels"),
    # Routes for the unified React SPA
    path("app/", views.schedule_app, name="schedule_app"),
    # Catch all routes under app/ to be handled by the React Router
    path("app/<path:path>", views.schedule_app, name="schedule_app_paths"),
]
