from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # Main schedule viewer page
    path("", views.schedule_viewer, name="schedule"),
    path("create/", views.create_schedule, name="create_schedule"),
]
