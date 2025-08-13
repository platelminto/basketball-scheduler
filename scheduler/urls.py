from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # API endpoints - standardized resource-based URLs
    path("api/seasons/", views.seasons_endpoint, name="seasons_api"),
    path("api/seasons/<int:season_id>/", views.schedule_data, name="season_details_api"),
    path("api/seasons/<int:season_id>/activate/", views.activate_season, name="activate_season_api"),
    path("api/seasons/<int:season_id>/validate/", views.validate_schedule, name="validate_schedule_api"),
    path("api/seasons/<int:season_id>/generate/", views.auto_generate_schedule, name="generate_schedule_api"),
    path("api/seasons/<int:season_id>/teams/", views.update_teams_levels, name="update_teams_api"),
    path("api/seasons/<int:season_id>/schedule/", views.save_or_update_schedule, name="update_schedule_api"),
    path("api/public/schedule/", views.public_schedule_data, name="public_schedule_api"),
    
    # Legacy endpoints - keep for backward compatibility temporarily
    path("validate_schedule/", views.validate_schedule, name="validate_schedule_legacy"),
    path("auto_generate_schedule/", views.auto_generate_schedule, name="auto_generate_schedule_legacy"),
    path("save_or_update_schedule/", views.save_or_update_schedule, name="save_or_update_schedule_legacy"),
    path("save_or_update_schedule/<int:season_id>/", views.save_or_update_schedule, name="save_or_update_schedule_with_id_legacy"),
    path("schedule/<int:season_id>/data/", views.get_season_schedule_data, name="get_season_schedule_data_legacy"),
    
    # Routes for the unified React SPA
    path("app/", views.schedule_app, name="schedule_app"),
    path("app/<path:path>", views.schedule_app, name="schedule_app_paths"),
    
    # Redirect to edit scores for active season
    path("edit-scores/", views.edit_scores_redirect, name="edit_scores_redirect"),
]
