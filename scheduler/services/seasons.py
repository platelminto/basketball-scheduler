"""
Season management service functions.

This module contains business logic for season operations including
listing, activation, and related data operations.
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
from scheduler.models import Season, Level, Game


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

        seasons_data.append(
            {
                "id": season.id,
                "name": season.name,
                "is_active": season.is_active,
                "created_at": season.created_at.isoformat(),
                "levels": levels_data,
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
        
        season.save()
        
        return {
            'status': 'success',
            'message': 'Organization updated successfully'
        }