"""
Season management service functions.

This module contains business logic for season operations including
listing, activation, and related data operations.
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from scheduler.models import Season, Level, Game


def is_season_complete(season):
    """Check if a season is complete (all dates passed, all scores entered)."""
    today = timezone.now().date()
    
    # Get all games for this season (GameManager automatically excludes deleted games)
    games = Game.objects.filter(level__season=season)
    
    if not games.exists():
        return False  # No games means not complete
    
    for game in games:
        # Check if game has a valid date/time first
        game_date = game.date_time
        if not game_date:
            continue  # Skip games without dates
        
        # Check if game date is today or in the future (not all dates passed)
        if game_date.date() >= today:
            return False
        
        # Check if any scores are missing
        if (game.team1_score is None or game.team1_score == '' or 
            game.team2_score is None or game.team2_score == ''):
            return False
    
    return True


def get_last_game_date(season):
    """Get the last game date for a season."""
    games = Game.objects.filter(level__season=season).exclude(week__monday_date__isnull=True)
    if not games.exists():
        return None
    
    latest_game = games.order_by('-week__monday_date', '-day_of_week').first()
    return latest_game.week.monday_date if latest_game else None


def get_seasons_data():
    """Get all seasons with their levels and teams."""
    seasons = (
        Season.objects.all()
        .prefetch_related("levels__season_teams__team")
        .order_by("-is_active", "-created_at")
    )

    seasons_data = []
    for season in seasons:
        levels_data = []
        for level in season.levels.all():
            teams_data = []
            
            # Add teams from SeasonTeam structure
            for season_team in level.season_teams.all():
                teams_data.append({
                    "id": season_team.team.id,
                    "name": season_team.team.name,
                    "season_team_id": season_team.id,
                })
            
            levels_data.append(
                {"id": level.id, "name": level.name, "teams": teams_data}
            )

        last_game_date = get_last_game_date(season)
        seasons_data.append(
            {
                "id": season.id,
                "name": season.name,
                "is_active": season.is_active,
                "created_at": season.created_at.isoformat(),
                "levels": levels_data,
                "is_complete": is_season_complete(season),
                "last_game_date": last_game_date.isoformat() if last_game_date else None,
            }
        )

    return seasons_data


def activate_season_logic(season_id):
    """Activate a season and deactivate all others."""
    season_to_activate = get_object_or_404(Season, pk=season_id)

    # Deactivate all other seasons first
    Season.objects.filter(is_active=True).update(is_active=False)

    # Activate the selected season
    season_to_activate.is_active = True
    season_to_activate.save()

    return {
        "success": True,
        "season": {
            "id": season_to_activate.id,
            "name": season_to_activate.name,
            "is_active": True,
        },
    }


def update_season_organization(season_id, data):
    """
    Update season organization (courts, levels, slot duration).
    
    Args:
        season_id: ID of the season to update
        data: Dictionary containing updates for courts, levels, slot_duration_minutes
        
    Returns:
        Dictionary with status and message
    """
    season = get_object_or_404(Season, pk=season_id)
    
    with transaction.atomic():
        # Update court names in game records
        if 'courts' in data and 'original_courts' in data:
            original_courts = data['original_courts']
            new_courts = [court['name'] if isinstance(court, dict) else court for court in data['courts']]
            
            # Create mapping from original to new court names
            for i, original_court in enumerate(original_courts):
                if i < len(new_courts) and original_court != new_courts[i]:
                    # Update all games in this season that use the old court name
                    Game.objects.filter(
                        level__season=season,
                        court=original_court
                    ).update(court=new_courts[i])
        
        # Update slot duration
        if 'slot_duration_minutes' in data:
            Level.objects.filter(season=season).update(
                slot_duration_minutes=data['slot_duration_minutes']
            )
        
        # Update level names
        if 'levels' in data:
            for level_data in data['levels']:
                if 'id' in level_data and 'name' in level_data:
                    Level.objects.filter(
                        season=season, 
                        id=level_data['id']
                    ).update(name=level_data['name'])
        
        # Update season name
        if 'schedule_name' in data and data['schedule_name'].strip():
            season.name = data['schedule_name'].strip()
        
        season.save()
        
        return {
            'status': 'success',
            'message': 'Organization updated successfully'
        }