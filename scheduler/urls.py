from django.urls import path
from . import views
from . import auth_views

app_name = "scheduler"

urlpatterns = [
    # Authentication endpoints
    path("auth/login/", auth_views.login_view, name="login"),
    path("auth/logout/", auth_views.logout_view, name="logout"),
    path("auth/status/", auth_views.auth_status, name="auth_status"),
    path("auth/csrf-token/", auth_views.get_csrf_token, name="csrf_token"),
    path("auth/test/", auth_views.protected_test, name="protected_test"),
    
    # API endpoints - standardized resource-based URLs
    path("api/seasons/", views.seasons_endpoint, name="seasons_api"),
    path("api/seasons/<int:season_id>/", views.schedule_data, name="season_details_api"),
    path("api/seasons/<int:season_id>/activate/", views.activate_season, name="activate_season_api"),
    path("api/seasons/<int:season_id>/delete/", views.delete_season, name="delete_season_api"),
    path("api/seasons/<int:season_id>/standings/", views.season_standings_endpoint, name="season_standings_api"),
    path("api/seasons/validate/", views.validate_schedule, name="seasons_validate_api"),
    path("api/seasons/<int:season_id>/generate/", views.auto_generate_schedule, name="generate_schedule_api"),
    path("api/seasons/cancel-generation/", views.cancel_schedule_generation, name="cancel_generation_api"),
    path("api/seasons/generation-progress/", views.generation_progress, name="generation_progress_api"),
    path("api/seasons/create/", views.save_or_update_schedule, name="create_schedule_api"),
    path("api/seasons/<int:season_id>/schedule/", views.save_or_update_schedule, name="update_schedule_api"),
    path("api/public/schedule/", views.public_schedule_data, name="public_schedule_api"),
    path("api/team-orgs/<int:team_org_id>/calendar.ics", views.team_calendar_export, name="team_calendar_export"),
    
    # Team management API endpoints
    path("api/teams/", views.teams_endpoint, name="teams_api"),
    path("api/teams/<int:team_id>/", views.team_detail_endpoint, name="team_detail_api"),
    path("api/teams/<int:team_id>/archive/", views.team_archive_endpoint, name="team_archive_api"),
    path("api/teams/<int:team_id>/stats/", views.team_stats_endpoint, name="team_stats_api"),
    path("api/teams/<int:team_id>/history/", views.team_history_endpoint, name="team_history_api"),
    path("api/seasons/<int:season_id>/available-teams/", views.season_available_teams_endpoint, name="season_available_teams_api"),
    path("api/seasons/<int:season_id>/assign-teams/", views.season_assign_teams_endpoint, name="season_assign_teams_api"),
    path("api/seasons/<int:season_id>/team-levels/", views.season_update_team_levels_endpoint, name="season_update_team_levels_api"),
    path("api/seasons/<int:season_id>/remove-teams/", views.season_remove_teams_endpoint, name="season_remove_teams_api"),
    
    # Routes for the unified React SPA
    path("app/", views.schedule_app, name="schedule_app"),
    path("app/<path:path>", views.schedule_app, name="schedule_app_paths"),
    
    # Redirect root /scheduler/ to seasons list
    path("", views.redirect_to_seasons, name="redirect_to_seasons"),
    
    # Embeddable schedule widget
    path("embed.js", views.embed_script, name="embed_script"),
    
    # Redirect to edit scores for active season
    path("edit-scores/", views.edit_scores_redirect, name="edit_scores_redirect"),
]
