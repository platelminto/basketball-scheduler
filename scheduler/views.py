import traceback
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.contrib import messages
from scheduler.models import Season
from scheduler.services import (
    # Season management
    get_seasons_data,
    activate_season_logic,
    
    # Schedule validation
    validate_schedule_data,
    
    # Schedule generation
    generate_schedule_async,
    handle_generation_cancellation,
    
    # Schedule CRUD operations
    create_schedule,
    update_schedule,
    build_schedule_response_data,
    
    # Schedule data retrieval
    get_schedule_data_for_season,
    get_public_schedule_data,
    
    # Team and level management
    update_teams_and_levels,
    
    # Calendar export
    generate_team_calendar,
    handle_calendar_options,
)


def schedule_app(request, path=None):
    """View for the unified React SPA

    The path parameter is used for the catch-all route and is ignored since
    all routes are handled by React Router on the client side.
    """
    return render(request, "scheduler/schedule_app_standalone.html")


def edit_scores_redirect(request):
    """Redirect to the edit scores page for the current active season."""
    active_season = Season.objects.filter(is_active=True).first()
    if not active_season:
        messages.error(request, "No active season found.")
        return redirect("scheduler:schedule_app")

    return redirect(
        "scheduler:schedule_app_paths", path=f"seasons/{active_season.id}/scores"
    )


def seasons_endpoint(request):
    """Unified seasons endpoint - GET for listing, POST for creating"""
    if request.method == "GET":
        return get_seasons(request)
    elif request.method == "POST":
        return save_or_update_schedule(request, season_id=None)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


def get_seasons(request):
    """API endpoint to get all seasons with their levels and teams."""
    seasons_data = get_seasons_data()
    return JsonResponse(seasons_data, safe=False)


def activate_season(request, season_id):
    """API endpoint to activate a season."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        result = activate_season_logic(season_id)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@ensure_csrf_cookie
def validate_schedule(request, season_id=None):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            validation_results = validate_schedule_data(data)
            return JsonResponse(validation_results)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error during validation: {e}")  # Consider using proper logging
            traceback.print_exc()
            return JsonResponse(
                {"error": f"An internal error occurred during validation: {e}"},
                status=500,
            )

    return JsonResponse({"error": "Invalid request method"}, status=405)


@ensure_csrf_cookie
def auto_generate_schedule(request, season_id=None):
    """
    View to get configuration from the schedule creator and generate a schedule
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            setup_data = data.get("setupData", "")
            week_data = data.get("weekData", "")
            parameters = data.get("parameters", {})

            # Create session key for cancellation handling
            session_key = request.session.session_key or request.session.create()

            result = generate_schedule_async(setup_data, week_data, parameters, session_key)
            return JsonResponse(result)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            print(f"Error during auto-generation: {e}")
            print(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@ensure_csrf_cookie
def cancel_schedule_generation(request):
    """
    Cancel an ongoing schedule generation for this session
    """
    if request.method == "POST":
        try:
            session_key = request.session.session_key
            result = handle_generation_cancellation(session_key)
            return JsonResponse(result, status=200)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@require_POST
@transaction.atomic
def save_or_update_schedule(request: HttpRequest, season_id=None):
    """
    Unified endpoint to create or update a schedule.
    - For create: requires season_name and setupData
    - For update: uses existing season_id
    - Always recreates all games for the season
    """
    try:
        data = json.loads(request.body)
        season_name = data.get("season_name")
        setup_data = data.get("setupData")
        game_assignments = data.get("game_assignments") or data.get("games", [])
        week_dates_data = data.get("week_dates", [])

        is_create = season_id is None

        # Validate required data
        if is_create:
            if not season_name or not setup_data or game_assignments is None:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Missing required data: season_name, setupData, or game_assignments",
                    },
                    status=400,
                )
        else:
            if not game_assignments:
                return JsonResponse(
                    {"status": "error", "message": "Missing required data: games"},
                    status=400,
                )

        # Create or update schedule using service
        if is_create:
            try:
                season, created_games_count = create_schedule(
                    season_name, setup_data, game_assignments, week_dates_data
                )
                deleted_count = 0
            except ValueError as e:
                if "already exists" in str(e):
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": str(e),
                        },
                        status=409,
                    )
                raise
        else:
            season, created_games_count, deleted_count = update_schedule(
                season_id, game_assignments, week_dates_data
            )

        # Build response using service
        response_data = build_schedule_response_data(
            is_create, season, created_games_count, deleted_count
        )

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON data"}, status=400
        )
    except IntegrityError as e:
        return JsonResponse(
            {"status": "error", "message": f"Database integrity error: {e}"}, status=400
        )
    except ValueError as e:
        return JsonResponse(
            {"status": "error", "message": f"Validation error: {e}"}, status=400
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(traceback.format_exc())
        return JsonResponse(
            {"status": "error", "message": f"An unexpected error occurred: {e}"},
            status=500,
        )


@ensure_csrf_cookie
def public_schedule_data(request):
    """API endpoint for public schedule data - returns active season only"""
    try:
        schedule_data = get_public_schedule_data()
        return JsonResponse(schedule_data)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=404)


@ensure_csrf_cookie
def schedule_data(request, season_id):
    """API endpoint for schedule data used by React"""
    from django.shortcuts import get_object_or_404
    season = get_object_or_404(Season, pk=season_id)
    schedule_data = get_schedule_data_for_season(season)
    return JsonResponse(schedule_data)




@csrf_exempt
def update_teams_levels(request, season_id):
    """API endpoint to update teams and levels for a season"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        data = json.loads(request.body)
        result = update_teams_and_levels(season_id, data)
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


def team_calendar_export(request, team_id):
    """
    Export team's game schedule as iCal calendar file

    Query parameters:
    - include_reffing=true: include games where team is referee_team
    - include_scores=true: include final scores for completed games
    - include_tournaments=true: include tournaments/off-weeks with start/end times
    """
    # Parse query parameters using service
    include_reffing, include_scores, include_tournaments = handle_calendar_options(request)

    # Generate calendar using service
    cal, team = generate_team_calendar(team_id, include_reffing, include_scores, include_tournaments)

    # Generate response
    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{team.name}-schedule.ics"'
    response["Cache-Control"] = "max-age=3600"  # Cache for 1 hour

    return response
