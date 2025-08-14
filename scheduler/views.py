import traceback
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest
import json
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.db.models import Q
from datetime import datetime
from scheduler.models import OffWeek, Season, Level, Team, Game, Week
from collections import defaultdict
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, get_current_timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from tests import (
    pairing_tests,
    cycle_pairing_test,
    referee_player_test,
    adjacent_slot_test,
)
from utils import get_config_from_schedule_creator
from scheduler.services import (
    normalize_game_data,
    resolve_game_objects,
    parse_game_fields,
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
    
    return redirect("scheduler:schedule_app_paths", path=f"seasons/{active_season.id}/scores")


def seasons_endpoint(request):
    """Unified seasons endpoint - GET for listing, POST for creating"""
    if request.method == 'GET':
        return get_seasons(request)
    elif request.method == 'POST':
        return save_or_update_schedule(request, season_id=None)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


def get_seasons(request):
    """API endpoint to get all seasons with their levels and teams."""
    seasons = (
        Season.objects.all()
        .prefetch_related("levels__teams")
        .order_by("-is_active", "-created_at")
    )

    seasons_data = []
    for season in seasons:
        levels_data = []
        for level in season.levels.all():
            teams_data = [
                {"id": team.id, "name": team.name} for team in level.teams.all()
            ]
            levels_data.append(
                {"id": level.id, "name": level.name, "teams": teams_data}
            )

        seasons_data.append(
            {
                "id": season.id,
                "name": season.name,
                "is_active": season.is_active,
                "created_at": season.created_at.isoformat(),
                "levels": levels_data,
            }
        )

    return JsonResponse(seasons_data, safe=False)


def activate_season(request, season_id):
    """API endpoint to activate a season."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    season_to_activate = get_object_or_404(Season, pk=season_id)

    try:
        # Deactivate all other seasons first
        Season.objects.filter(is_active=True).update(is_active=False)

        # Activate the selected season
        season_to_activate.is_active = True
        season_to_activate.save()

        return JsonResponse(
            {
                "success": True,
                "season": {
                    "id": season_to_activate.id,
                    "name": season_to_activate.name,
                    "is_active": True,
                },
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@ensure_csrf_cookie
def validate_schedule(request, season_id=None):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            schedule_data = data["schedule"]
            config_data = data["config"]

            # Extract levels and teams_per_level from the provided config
            levels = config_data["levels"]
            teams_per_level = config_data["teams_per_level"]

            validation_results = {}

            # Run Pairing Test
            pt_passed, pt_errors = pairing_tests(schedule_data, levels, teams_per_level)
            validation_results["Pairings"] = {
                "passed": pt_passed,
                "message": "Teams play the correct number of times based on their level size.",
                "errors": pt_errors,
            }

            # Run Cycle Pairing Test
            cpt_passed, cpt_errors = cycle_pairing_test(
                schedule_data, levels, teams_per_level
            )
            validation_results["Cycle Pairings"] = {
                "passed": cpt_passed,
                "message": "Matchups repeat in proper round-robin cycles for each level.",
                "errors": cpt_errors,
            }

            # Run Referee-Player Test
            rpt_passed, rpt_errors = referee_player_test(schedule_data)
            validation_results["Referee-Player"] = {
                "passed": rpt_passed,
                "message": "No team referees a game in which they are playing.",
                "errors": rpt_errors,
            }

            # Run Adjacent Slots Test
            ast_passed, ast_errors = adjacent_slot_test(schedule_data)
            validation_results["Adjacent Slots"] = {
                "passed": ast_passed,
                "message": "Teams only referee in slots directly adjacent to when they play.",
                "errors": ast_errors,
            }

            return JsonResponse(validation_results)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error during validation: {e}")  # Consider using proper logging
            import traceback

            traceback.print_exc()
            return JsonResponse(
                {"error": f"An internal error occurred during validation: {e}"},
                status=500,
            )  # Return 500 for server errors

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

            # Get configuration from the setup data
            config = get_config_from_schedule_creator(setup_data, week_data)

            from schedule import Scheduler

            # Create a scheduler with our config
            scheduler = Scheduler(config)

            # Generate the schedule
            schedule, _ = scheduler.find_schedule(
                num_cores=1, use_saved_schedule=False, max_attempts=30000
            )

            if not schedule:
                return JsonResponse({"error": "No schedule found"}, status=400)

            scheduled_week_data = []

            seen_off_weeks = 0
            for data_week in week_data.values():
                if data_week.get("isOffWeek", False):
                    seen_off_weeks += 1
                    continue

                schedule_week = schedule[data_week["week_number"] - 1 - seen_off_weeks]
                schedule_games = [
                    game for slot in schedule_week["slots"].values() for game in slot
                ]
                week = []

                for i, data_game in enumerate(data_week["games"]):
                    schedule_game = schedule_games[i]
                    data_game["level_name"] = schedule_game["level"]
                    data_game["team1_name"] = schedule_game["teams"][0]
                    data_game["team2_name"] = schedule_game["teams"][1]
                    data_game["referee_name"] = schedule_game["ref"]

                    week.append(data_game)

                scheduled_week_data.append(week)

            return JsonResponse(
                {"config": scheduler.config, "schedule": scheduled_week_data}
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            print(f"Error during auto-generation: {e}")
            print(traceback.format_exc())
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

        # Handle season creation/retrieval
        if is_create:
            teams_by_level_name = setup_data.get("teams")
            if not teams_by_level_name:
                return JsonResponse(
                    {"status": "error", "message": "Missing 'teams' data in setupData"},
                    status=400,
                )

            season, created = Season.objects.get_or_create(name=season_name)
            if not created:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"A season with the name '{season_name}' already exists. Please choose a different name.",
                    },
                    status=409,
                )

            # Create levels and teams
            level_instances = {}
            team_instances = {}
            for level_name, team_names in teams_by_level_name.items():
                level_obj = Level.objects.create(season=season, name=level_name)
                level_instances[level_name] = level_obj
                team_instances[level_name] = {}
                for team_name in team_names:
                    team_obj = Team.objects.create(level=level_obj, name=team_name)
                    team_instances[level_name][team_name] = team_obj

            # Create weeks from week_dates_data
            for week_info in week_dates_data:
                week_number = week_info.get("week_number")
                monday_date = week_info.get("monday_date")
                is_off_week = week_info.get("is_off_week", False)

                if is_off_week:
                    OffWeek.objects.create(season=season, monday_date=monday_date)
                else:
                    Week.objects.create(
                        season=season, week_number=week_number, monday_date=monday_date
                    )

            lookups = (level_instances, team_instances, season)
            deleted_count = 0
        else:
            season = get_object_or_404(Season, pk=season_id)

            # Delete existing games first (before weeks, since week FK is now PROTECT)
            deleted_count, _ = Game.objects.filter(level__season=season).delete()
            
            # Handle week date updates, deletions, and off-week insertions
            if week_dates_data:
                # Clear all existing off-weeks for this season first to avoid UNIQUE constraint issues
                OffWeek.objects.filter(season=season).delete()
                
                # Clear all existing regular weeks (games already deleted above)
                Week.objects.filter(season=season).delete()
                
                # Recreate all weeks from frontend data
                for week_date in week_dates_data:
                    week_id = week_date.get("id")
                    new_date = week_date.get("date")
                    is_off_week = week_date.get("isOffWeek", False)
                    
                    if week_id and new_date:
                        try:
                            from datetime import datetime
                            parsed_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                            
                            if is_off_week:
                                # Create new off week
                                OffWeek.objects.create(
                                    season=season,
                                    monday_date=parsed_date
                                )
                            else:
                                # Create new regular week
                                Week.objects.create(
                                    season=season,
                                    week_number=int(week_id),
                                    monday_date=parsed_date
                                )
                                
                        except Exception as e:
                            return JsonResponse(
                                {
                                    "status": "error",
                                    "error": f"Error processing week {week_id}: {str(e)}",
                                },
                                status=400,
                            )

            # Build lookups for new game creation (games already deleted above)
            valid_levels = {
                str(level.id): level for level in Level.objects.filter(season=season)
            }
            valid_teams = {
                str(team.id): team for team in Team.objects.filter(level__season=season)
            }
            valid_weeks = {
                str(week.week_number): week
                for week in Week.objects.filter(season=season)
            }
            lookups = (valid_levels, valid_teams, valid_weeks)

        # Process games
        created_games_count = 0
        creation_errors = []

        for idx, assignment in enumerate(game_assignments):
            try:
                # Normalize and resolve objects
                game_data = normalize_game_data(assignment, is_create, lookups)
                (
                    level_obj,
                    team1_obj,
                    team2_obj,
                    referee_obj,
                    referee_name,
                    week_obj,
                    resolve_errors,
                ) = resolve_game_objects(game_data, is_create, lookups)

                if resolve_errors:
                    creation_errors.extend(
                        [f"Game #{idx+1}: {err}" for err in resolve_errors]
                    )
                    continue

                # Parse fields
                game_time, day_of_week, team1_score, team2_score, parse_errors = (
                    parse_game_fields(game_data, is_create)
                )
                if parse_errors:
                    creation_errors.extend(
                        [f"Game #{idx+1}: {err}" for err in parse_errors]
                    )
                    continue

                # Create game (validation already passed)
                Game.objects.create(
                    level=level_obj,
                    week=week_obj,
                    team1=team1_obj,
                    team2=team2_obj,
                    referee_team=referee_obj,
                    referee_name=referee_name,
                    day_of_week=day_of_week,
                    time=game_time,
                    court=game_data["court"],
                    team1_score=team1_score,
                    team2_score=team2_score,
                )
                created_games_count += 1

            except Exception as e:
                creation_errors.append(
                    f"Game #{idx+1}: Unexpected error during creation - {str(e)}"
                )

        # Handle creation errors (shouldn't happen if validation passed)
        if creation_errors:
            transaction.set_rollback(True)
            # Include errors in the message instead of separate field
            error_details = ". ".join(creation_errors)
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Schedule passed validation but had creation errors: {error_details}",
                },
                status=400,
            )

        # Return success response
        response_data = {
            "status": "success",
            "games_created": created_games_count,
        }

        if is_create:
            response_data.update(
                {
                    "message": f"Schedule saved successfully for season '{season_name}'.",
                    "season_id": season.id,
                }
            )
        else:
            response_data.update(
                {
                    "deleted_count": deleted_count,
                    "message": f"Successfully updated schedule with {created_games_count} games.",
                }
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
    # Get the active season
    active_season = Season.objects.filter(is_active=True).first()
    if not active_season:
        return JsonResponse({"error": "No active season found"}, status=404)
    
    # Reuse the existing schedule_data logic
    return _get_schedule_data(request, active_season)


@ensure_csrf_cookie
def schedule_data(request, season_id):
    """API endpoint for schedule data used by React"""
    season = get_object_or_404(Season, pk=season_id)
    return _get_schedule_data(request, season)


def _get_schedule_data(request, season):
    """Shared implementation for schedule data endpoints"""

    # Get all weeks in this season (both regular and off weeks)
    weeks = Week.objects.filter(season=season).order_by("week_number")
    off_weeks = OffWeek.objects.filter(season=season).order_by("monday_date")

    # Create a combined list of all weeks (regular and off) sorted by date
    all_week_data = []
    
    # Add regular weeks
    for week in weeks:
        all_week_data.append({
            'type': 'regular',
            'date': week.monday_date,
            'week_obj': week,
        })
    
    # Add off weeks
    for off_week in off_weeks:
        all_week_data.append({
            'type': 'off',
            'date': off_week.monday_date,
            'week_obj': off_week,
        })
    
    # Sort all weeks by date
    all_week_data.sort(key=lambda x: x['date'])
    
    # Process weeks in chronological order and assign sequential week numbers
    games_by_week = {}
    for week_num, week_data in enumerate(all_week_data, 1):
        if week_data['type'] == 'regular':
            week = week_data['week_obj']
            games = (
                Game.objects.filter(week=week)
                .select_related("level", "team1", "team2", "referee_team")
                .order_by("day_of_week", "time")
            )

            games_list = []
            for game in games:
                games_list.append(
                    {
                        "id": game.id,
                        "day_of_week": game.day_of_week,
                        "time": game.time.strftime("%H:%M") if game.time else "",
                        "court": game.court,
                        "level_id": game.level.id if game.level else None,
                        "level_name": game.level.name if game.level else "",
                        "team1_id": game.team1.id if game.team1 else None,
                        "team1_name": game.team1.name if game.team1 else "",
                        "team2_id": game.team2.id if game.team2 else None,
                        "team2_name": game.team2.name if game.team2 else "",
                        "team1_score": game.team1_score,
                        "team2_score": game.team2_score,
                        "referee_team_id": (
                            game.referee_team.id if game.referee_team else None
                        ),
                        "referee_name": game.referee_name,
                    }
                )

            games_by_week[week_num] = {
                "id": week.id,
                "week_number": week_num,
                "monday_date": week.monday_date.strftime("%Y-%m-%d"),
                "games": games_list,
            }
        else:  # off week
            off_week = week_data['week_obj']
            games_by_week[week_num] = {
                "id": f"off_{off_week.id}",
                "week_number": week_num,
                "monday_date": off_week.monday_date.strftime("%Y-%m-%d"),
                "isOffWeek": True,
                "games": [],
            }

    # Get all levels
    levels = Level.objects.filter(season=season).order_by("name")
    levels_data = [{"id": level.id, "name": level.name} for level in levels]

    # Get all teams by level
    teams_by_level = {}
    for level in levels:
        teams = Team.objects.filter(level=level).order_by("name")
        teams_by_level[level.id] = [
            {"id": team.id, "name": team.name} for team in teams
        ]

    # Get all courts
    courts = list(
        Game.objects.filter(level__season=season)
        .values_list("court", flat=True)
        .distinct()
        .order_by("court")
    )
    courts = [court for court in courts if court]

    return JsonResponse(
        {
            "season": {
                "id": season.id,
                "name": season.name,
            },
            "weeks": games_by_week,
            "levels": levels_data,
            "teams_by_level": teams_by_level,
            "courts": courts,
        }
    )


@csrf_exempt
def update_teams_levels(request, season_id):
    """API endpoint to update teams and levels for a season"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        season = get_object_or_404(Season, pk=season_id)
        
        levels_data = data.get('levels', [])
        teams_data = data.get('teams', {})  # Fallback to old format
        
        # Start transaction to ensure data consistency
        with transaction.atomic():
            # Get existing levels for this season
            existing_levels_by_id = {level.id: level for level in Level.objects.filter(season=season)}
            existing_levels_by_name = {level.name: level for level in Level.objects.filter(season=season)}
            processed_level_ids = set()
            
            # Use new format if available, otherwise fall back to old format
            if levels_data:
                # New format with IDs - can handle renames properly
                for level_info in levels_data:
                    level_id = level_info.get('id')
                    level_name = level_info.get('name', '').strip()
                    team_infos = level_info.get('teams', [])
                    
                    if not level_name:
                        continue
                    
                    # Check if this is a rename or update of existing level
                    if level_id and level_id in existing_levels_by_id:
                        level = existing_levels_by_id[level_id]
                        processed_level_ids.add(level_id)
                        
                        # Update level name if it changed
                        if level.name != level_name:
                            level.name = level_name
                            level.save()
                    else:
                        # This is a new level
                        level = Level.objects.create(season=season, name=level_name)
                        processed_level_ids.add(level.id)
                    
                    # Process teams for this level
                    existing_teams_by_id = {team.id: team for team in Team.objects.filter(level=level)}
                    existing_teams_by_name = {team.name: team for team in Team.objects.filter(level=level)}
                    processed_team_ids = set()
                    
                    for team_info in team_infos:
                        team_id = team_info.get('id')
                        team_name = team_info.get('name', '').strip()
                        
                        if not team_name:
                            continue
                        
                        # Check if this is a rename or update of existing team
                        if team_id and team_id in existing_teams_by_id:
                            team = existing_teams_by_id[team_id]
                            processed_team_ids.add(team_id)
                            
                            # Update team name if it changed
                            if team.name != team_name:
                                team.name = team_name
                                team.save()
                        else:
                            # This is a new team
                            team = Team.objects.create(level=level, name=team_name)
                            processed_team_ids.add(team.id)
                    
                    # Remove teams that are no longer present
                    teams_to_remove = set(existing_teams_by_id.keys()) - processed_team_ids
                    for team_id in teams_to_remove:
                        team = existing_teams_by_id[team_id]
                        # Check if team has any games
                        if Game.objects.filter(Q(team1=team) | Q(team2=team) | Q(referee_team=team)).exists():
                            # Team has games, so we can't delete it
                            pass  # Keep the team
                        else:
                            # Safe to delete since no games reference it
                            team.delete()
                            
            else:
                # Old format fallback - only names provided
                for level_name, team_names in teams_data.items():
                    level_name = level_name.strip()
                    if not level_name:
                        continue
                        
                    # Get or create the level
                    if level_name in existing_levels_by_name:
                        level = existing_levels_by_name[level_name]
                        processed_level_ids.add(level.id)
                    else:
                        level = Level.objects.create(season=season, name=level_name)
                        processed_level_ids.add(level.id)
                    
                    # Process teams for this level (old format)
                    existing_teams = {team.name: team for team in Team.objects.filter(level=level)}
                    updated_teams = set()
                    
                    for team_name in team_names:
                        if team_name.strip():
                            team_name = team_name.strip()
                            updated_teams.add(team_name)
                            
                            if team_name not in existing_teams:
                                Team.objects.create(level=level, name=team_name)
                    
                    # Remove teams that are no longer present
                    teams_to_remove = set(existing_teams.keys()) - updated_teams
                    for team_name in teams_to_remove:
                        team = existing_teams[team_name]
                        if Game.objects.filter(Q(team1=team) | Q(team2=team) | Q(referee_team=team)).exists():
                            pass  # Keep the team
                        else:
                            team.delete()
            
            # Remove levels that are no longer present
            levels_to_remove = set(existing_levels_by_id.keys()) - processed_level_ids
            for level_id in levels_to_remove:
                level = existing_levels_by_id[level_id]
                # Check if level has any teams with games
                teams_with_games = Team.objects.filter(level=level).filter(
                    Q(games_as_team1__isnull=False) | 
                    Q(games_as_team2__isnull=False) | 
                    Q(games_as_referee__isnull=False)
                ).exists()
                
                if not teams_with_games:
                    # Safe to delete the level and its teams
                    level.delete()  # This will cascade delete teams
                # If teams have games, we keep the level
        
        return JsonResponse({
            'status': 'success',
            'message': 'Teams and levels updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
