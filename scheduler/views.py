import logging
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.contrib import messages
from scheduler.models import Season

logger = logging.getLogger(__name__)
from scheduler.decorators import api_login_required, schedule_app_login_required
from scheduler.services import (
    # Season management
    get_seasons_data,
    activate_season_logic,
    update_season_organization,
    
    # Schedule validation
    validate_schedule_data,
    
    # Schedule generation
    generate_schedule_async,
    handle_generation_cancellation,
    get_generation_progress,
    
    # Schedule CRUD operations
    create_schedule,
    update_schedule,
    build_schedule_response_data,
    
    # Schedule data retrieval
    get_schedule_data_for_season,
    get_public_schedule_data,
    
    
    # Calendar export
    generate_team_calendar,
    handle_calendar_options,
)

# Import team management services
from scheduler.services.team_management import (
    get_all_teams,
    create_team,
    update_team,
    delete_team,
    archive_team,
    unarchive_team,
    get_team_history,
    get_available_teams_for_season,
    assign_teams_to_season,
    update_team_level_assignments,
    remove_teams_from_season,
)

# Import stats services
from scheduler.services.stats import (
    calculate_season_standings,
    get_team_history_stats,
    get_team_history_with_league_tables,
)


def schedule_app(request, path=None):
    """View for the unified React SPA

    The path parameter is used for the catch-all route and is ignored since
    all routes are handled by React Router on the client side.
    """
    return render(request, "scheduler/schedule_app_standalone.html")


def redirect_to_seasons(request):
    """Redirect /scheduler/ to the seasons list."""
    return redirect('/scheduler/app/seasons')


def embed_script(request):
    """Serve the embed JavaScript file with proper content type."""
    from webpack_loader.utils import get_files
    from django.http import HttpResponseRedirect
    
    embed_files = get_files('scheduleEmbed')
    embed_url = embed_files[0]['url']
    
    # Redirect to the actual bundle file
    return HttpResponseRedirect(embed_url)


def edit_scores_redirect(request):
    """Redirect to the edit scores page for the current active season."""
    active_season = Season.objects.filter(is_active=True).first()
    if not active_season:
        messages.error(request, "No active season found.")
        return redirect("scheduler:schedule_app_paths", path="seasons")

    return redirect(
        "scheduler:schedule_app_paths", path=f"seasons/{active_season.id}/scores"
    )


@api_login_required
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


@api_login_required
def activate_season(request, season_id):
    """API endpoint to activate a season."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        result = activate_season_logic(season_id)
        return JsonResponse(result)
    except Exception as e:
        logger.exception(f"Error activating season {season_id}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@api_login_required
@csrf_exempt
def delete_season(request, season_id):
    """API endpoint to soft delete a season."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        # Get the season using all_objects to include any already-deleted seasons
        season = Season.all_objects.get(id=season_id)
        
        # Check if season is active
        if season.is_active:
            return JsonResponse({
                "success": False, 
                "error": "Cannot delete the active season"
            }, status=400)
        
        # Check if already deleted
        if season.is_deleted:
            return JsonResponse({
                "success": False,
                "error": "Season is already deleted"
            }, status=400)
        
        # Soft delete the season and rename it
        import random
        import string
        
        original_name = season.name
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        season.is_deleted = True
        season.name = f"DELETED_{original_name}_{random_suffix}"
        season.save()
        
        return JsonResponse({
            "success": True,
            "message": f"Season '{original_name}' has been deleted"
        })
        
    except Season.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Season not found"
        }, status=404)
    except Exception as e:
        logger.exception(f"Error deleting season {season_id}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


@api_login_required
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
            logger.exception("Error during schedule validation")
            return JsonResponse(
                {"error": f"An internal error occurred during validation: {e}"},
                status=500,
            )

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_login_required
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

            # Ensure we have a session key for cancellation handling
            if not request.session.session_key:
                request.session.save()  # This will create a session key
            session_key = request.session.session_key

            result = generate_schedule_async(setup_data, week_data, parameters, session_key)
            return JsonResponse(result)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            logger.exception("Error during auto-generation")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_login_required
@ensure_csrf_cookie
def cancel_schedule_generation(request):
    """
    Cancel an ongoing schedule generation for this session
    """
    if request.method == "POST":
        try:
            session_key = request.session.session_key
            
            # Ensure we have a session key
            if not session_key:
                request.session.save()  # This will create a session key
                session_key = request.session.session_key
                
            if not session_key:
                return JsonResponse({"error": "No session available"}, status=400)
            
            # Parse request body for use_best parameter
            use_best = False
            if request.content_type == 'application/json':
                import json
                try:
                    body = json.loads(request.body)
                    use_best = body.get('use_best', False)
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            result = handle_generation_cancellation(session_key)
            return JsonResponse(result, status=200)
        except ValueError as e:
            logger.exception("ValueError in cancel_schedule_generation")
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("Error in cancel_schedule_generation")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_login_required
@ensure_csrf_cookie
def generation_progress(request):
    """
    Get the current progress of schedule generation for this session
    """
    if request.method == "GET":
        try:
            session_key = request.session.session_key
            
            # Ensure we have a session key
            if not session_key:
                request.session.save()  # This will create a session key
                session_key = request.session.session_key
                
            if not session_key:
                return JsonResponse({"error": "No session available"}, status=400)
                
            progress = get_generation_progress(session_key)
            if progress:
                # Format best_schedule if present (exactly like full auto-generation does)
                if 'best_schedule' in progress and progress['best_schedule'] is not None:
                    from .services.generation import format_generated_schedule
                    from django.core.cache import cache
                    
                    try:
                        # Get week_data from cache (stored when generation started)
                        week_data_key = f"schedule_generation_week_data_{session_key}"
                        week_data = cache.get(week_data_key)
                        if week_data:
                            formatted_schedule = format_generated_schedule(progress['best_schedule'], week_data)
                            progress['best_schedule'] = formatted_schedule
                    except Exception as e:
                        logger.exception("Error formatting best_schedule in progress")
                        # Keep unformatted version as fallback
                        pass
                
                return JsonResponse({"progress": progress}, status=200)
            else:
                return JsonResponse({"progress": None}, status=200)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_login_required
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
        logger.exception("Database integrity error in save_or_update_schedule")
        return JsonResponse(
            {"status": "error", "message": f"Database integrity error: {e}"}, status=400
        )
    except ValueError as e:
        return JsonResponse(
            {"status": "error", "message": f"Validation error: {e}"}, status=400
        )
    except Exception as e:
        logger.exception("Unexpected error in save_or_update_schedule")
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


@api_login_required
@ensure_csrf_cookie
def schedule_data(request, season_id):
    """API endpoint for schedule data used by React"""
    from django.shortcuts import get_object_or_404
    
    if request.method == 'GET':
        season = get_object_or_404(Season, pk=season_id)
        schedule_data = get_schedule_data_for_season(season)
        return JsonResponse(schedule_data)
        
    elif request.method == 'POST':
        # Handle organization updates (courts, levels, slot duration)
        try:
            import json
            data = json.loads(request.body)
            result = update_season_organization(season_id, data)
            return JsonResponse(result)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)





def team_calendar_export(request, team_org_id):
    """
    Export team organization's game schedule as iCal calendar file

    Query parameters:
    - include_reffing=true: include games where team is referee_season_team
    - include_scores=true: include final scores for completed games
    - include_tournaments=true: include tournaments/off-weeks with start/end times
    """
    # Parse query parameters using service
    include_reffing, include_scores, include_tournaments = handle_calendar_options(request)

    # Generate calendar using service
    cal, team_org = generate_team_calendar(team_org_id, include_reffing, include_scores, include_tournaments)

    # Generate response
    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{team_org.name}-schedule.ics"'
    response["Cache-Control"] = "max-age=3600"  # Cache for 1 hour

    return response


# Team Management API Endpoints

@api_login_required
@csrf_exempt
def teams_endpoint(request):
    """API endpoint for team management operations."""
    if request.method == "GET":
        # Get all teams, optionally including archived
        include_archived = request.GET.get('include_archived', 'false').lower() == 'true'
        teams = get_all_teams(include_archived=include_archived)
        
        teams_data = []
        for team in teams:
            # Get seasons this team participated in
            season_participations = team.season_participations.select_related('season').order_by('-season__name')
            seasons = [{'name': sp.season.name, 'id': sp.season.id} for sp in season_participations]
            
            teams_data.append({
                'id': team.id,
                'name': team.name,
                'is_archived': team.is_archived,
                'created_at': team.created_at.isoformat(),
                'updated_at': team.updated_at.isoformat(),
                'seasons': seasons,
            })
        
        return JsonResponse({'teams': teams_data})
    
    elif request.method == "POST":
        # Create new team
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Team name is required'}, status=400)
            
            result = create_team(name)
            
            if result['status'] == 'error':
                return JsonResponse(result, status=400)
            
            # Return the created team data
            team = result['team']
            # Get seasons this team participated in (empty for new team)
            season_participations = team.season_participations.select_related('season').order_by('-season__name')
            seasons = [{'name': sp.season.name, 'id': sp.season.id} for sp in season_participations]
            
            team_data = {
                'id': team.id,
                'name': team.name,
                'is_archived': team.is_archived,
                'created_at': team.created_at.isoformat(),
                'updated_at': team.updated_at.isoformat(),
                'seasons': seasons,
            }
            
            return JsonResponse({
                'status': 'success',
                'team': team_data,
                'message': result['message']
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
@csrf_exempt
def team_detail_endpoint(request, team_id):
    """API endpoint for individual team operations."""
    if request.method == "PUT":
        # Update team name
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            
            if not name:
                return JsonResponse({'status': 'error', 'message': 'Team name is required'}, status=400)
            
            result = update_team(team_id, name)
            
            if result['status'] == 'error':
                return JsonResponse(result, status=400)
            
            # Return updated team data
            team = result['team']
            # Get seasons this team participated in
            season_participations = team.season_participations.select_related('season').order_by('-season__name')
            seasons = [{'name': sp.season.name, 'id': sp.season.id} for sp in season_participations]
            
            team_data = {
                'id': team.id,
                'name': team.name,
                'is_archived': team.is_archived,
                'created_at': team.created_at.isoformat(),
                'updated_at': team.updated_at.isoformat(),
                'seasons': seasons,
            }
            
            return JsonResponse({
                'status': 'success',
                'team': team_data,
                'message': result['message']
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    elif request.method == "DELETE":
        # Delete team
        try:
            result = delete_team(team_id)
            
            if result['status'] == 'error':
                return JsonResponse(result, status=400)
            
            return JsonResponse({
                'status': 'success',
                'message': result['message']
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
@csrf_exempt
def team_archive_endpoint(request, team_id):
    """API endpoint for archiving/unarchiving teams."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            archive = data.get('archive', True)  # Default to archive
            
            if archive:
                result = archive_team(team_id)
            else:
                result = unarchive_team(team_id)
            
            # Return updated team data
            team = result['team']
            # Get seasons this team participated in
            season_participations = team.season_participations.select_related('season').order_by('-season__name')
            seasons = [{'name': sp.season.name, 'id': sp.season.id} for sp in season_participations]
            
            team_data = {
                'id': team.id,
                'name': team.name,
                'is_archived': team.is_archived,
                'created_at': team.created_at.isoformat(),
                'updated_at': team.updated_at.isoformat(),
                'seasons': seasons,
            }
            
            return JsonResponse({
                'status': 'success',
                'team': team_data,
                'message': result['message']
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
@csrf_exempt
def team_history_endpoint(request, team_id):
    """API endpoint for getting team participation history."""
    if request.method == "GET":
        try:
            result = get_team_history(team_id)
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
def team_stats_endpoint(request, team_id):
    """API endpoint for getting team statistics with league tables across all seasons."""
    if request.method == "GET":
        try:
            from django.shortcuts import get_object_or_404
            from scheduler.models import TeamOrganization
            
            team = get_object_or_404(TeamOrganization, pk=team_id)
            stats = get_team_history_with_league_tables(team)
            return JsonResponse(stats)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
@csrf_exempt
def season_available_teams_endpoint(request, season_id):
    """API endpoint for getting teams available for assignment to a season."""
    if request.method == "GET":
        try:
            teams = get_available_teams_for_season(season_id)
            
            teams_data = []
            for team in teams:
                teams_data.append({
                    'id': team.id,
                    'name': team.name,
                    'is_archived': team.is_archived,
                })
            
            return JsonResponse({'teams': teams_data})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
@csrf_exempt
def season_assign_teams_endpoint(request, season_id):
    """API endpoint for assigning teams to a season."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            team_assignments = data.get('assignments', [])
            
            result = assign_teams_to_season(season_id, team_assignments)
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
@csrf_exempt
def season_update_team_levels_endpoint(request, season_id):
    """API endpoint for updating team level assignments in a season."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            level_assignments = data.get('assignments', [])
            
            result = update_team_level_assignments(season_id, level_assignments)
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@api_login_required
@csrf_exempt
def season_remove_teams_endpoint(request, season_id):
    """API endpoint for removing teams from a season."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            team_ids = data.get('team_ids', [])
            
            result = remove_teams_from_season(season_id, team_ids)
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)



def season_standings_endpoint(request, season_id):
    """API endpoint for getting calculated standings for a season."""
    if request.method == "GET":
        try:
            from django.shortcuts import get_object_or_404
            from scheduler.models import Season, SeasonTeam

            season = get_object_or_404(Season, pk=season_id)
            standings = calculate_season_standings(season)

            return JsonResponse({'standings': standings})

        except Exception as e:
            logger.exception(f"Error in standings endpoint for season {season_id}")
            return JsonResponse({'error': str(e)}, status=400)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
