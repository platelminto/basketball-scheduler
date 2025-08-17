"""
Season management service functions.

This module contains business logic for season operations including
listing, activation, and related data operations.
"""

from django.shortcuts import get_object_or_404
from scheduler.models import Season


def get_seasons_data():
    """Get all seasons with their levels and teams."""
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