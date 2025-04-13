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
    path("auto_generate_schedule/", views.auto_generate_schedule, name="auto_generate_schedule"),
]
