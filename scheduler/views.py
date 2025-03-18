from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import SavedSchedule
import json
import os
import datetime

# Direct imports from schedule.py
import schedule
from schedule import find_schedule, load_schedule_from_file, save_schedule_to_file


def schedule_viewer(request):
    """Main schedule viewing page"""
    return render(request, "scheduler/schedule_viewer.html")


def create_schedule(request):
    """View to start creating a new schedule"""
    return render(request, "scheduler/create_schedule.html")
