from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # Main schedule viewer page
    path("schedule/", views.schedule_viewer, name="schedule"),
    # API endpoints for the schedule functionality
    path("generate-schedule/", views.generate_schedule, name="generate_schedule"),
    path("load-schedule/", views.load_schedule, name="load_schedule"),
    path(
        "save-schedule-with-times/",
        views.save_schedule_with_times,
        name="save_schedule_with_times",
    ),
]
