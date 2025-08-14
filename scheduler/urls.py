from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # API endpoints - standardized resource-based URLs
    path("api/seasons/", views.seasons_endpoint, name="seasons_api"),
    path("api/seasons/<int:season_id>/", views.schedule_data, name="season_details_api"),
    path("api/seasons/<int:season_id>/activate/", views.activate_season, name="activate_season_api"),
    path("api/seasons/validate/", views.validate_schedule, name="seasons_validate_api"),
    path("api/seasons/<int:season_id>/generate/", views.auto_generate_schedule, name="generate_schedule_api"),
    path("api/seasons/<int:season_id>/teams/", views.update_teams_levels, name="update_teams_api"),
    path("api/seasons/create/", views.save_or_update_schedule, name="create_schedule_api"),
    path("api/seasons/<int:season_id>/schedule/", views.save_or_update_schedule, name="update_schedule_api"),
    path("api/public/schedule/", views.public_schedule_data, name="public_schedule_api"),
    path("api/teams/<int:team_id>/calendar.ics", views.team_calendar_export, name="team_calendar_export"),
    
    
    # Routes for the unified React SPA
    path("app/", views.schedule_app, name="schedule_app"),
    path("app/<path:path>", views.schedule_app, name="schedule_app_paths"),
    
    # Redirect to edit scores for active season
    path("edit-scores/", views.edit_scores_redirect, name="edit_scores_redirect"),
]
