"""
Team management service functions for the new team organization system.

This module handles CRUD operations for TeamOrganization and provides
utilities for managing team assignments across seasons.
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Count, Sum
from scheduler.models import TeamOrganization, SeasonTeam, Season, Level, Game


def get_all_teams(include_archived=False):
    """Get all teams, optionally including archived ones."""
    queryset = TeamOrganization.objects.all()
    if not include_archived:
        queryset = queryset.filter(is_archived=False)
    return queryset.order_by('name')


def create_team(name):
    """Create a new team organization."""
    # Always allow creating teams with any name - validation happens at season assignment level
    team = TeamOrganization.objects.create(name=name, is_archived=False)
    return {"status": "success", "team": team, "message": f"Team '{name}' created successfully"}


def update_team(team_id, name):
    """Update a team's name."""
    team = get_object_or_404(TeamOrganization, pk=team_id)
    
    # Check if the new name conflicts with another team in any season this team participates in
    conflicting_seasons = []
    team_seasons = SeasonTeam.objects.filter(team=team).select_related('season')
    
    for season_team in team_seasons:
        season = season_team.season
        # Check if another team with the same name is in this season
        other_teams_same_name = SeasonTeam.objects.filter(
            season=season,
            team__name=name
        ).exclude(team=team)
        
        if other_teams_same_name.exists():
            conflicting_seasons.append(season.name)
    
    if conflicting_seasons:
        return {"status": "error", "message": f"Team '{name}' already exists in seasons: {', '.join(conflicting_seasons)}"}
    
    old_name = team.name
    team.name = name
    team.save()
    
    return {"status": "success", "team": team, "message": f"Team renamed from '{old_name}' to '{name}'"}


def delete_team(team_id):
    """Soft delete a team."""
    team = get_object_or_404(TeamOrganization.all_objects, pk=team_id)
    
    # Check if already deleted
    if team.is_deleted:
        return {"status": "error", "message": "Team is already deleted"}
    
    # Check if team is in any non-deleted seasons
    active_seasons = SeasonTeam.objects.filter(
        team=team, 
        season__is_deleted=False
    ).select_related('season')
    
    if active_seasons.exists():
        season_names = ", ".join([st.season.name for st in active_seasons])
        return {"status": "error", "message": f"Cannot delete team '{team.name}' - it is still assigned to non-deleted seasons: {season_names}"}
    
    # Soft delete the team and rename it to avoid name conflicts
    import random
    import string
    
    original_name = team.name
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    team.is_deleted = True
    team.name = f"DELETED_{original_name}_{random_suffix}"
    team.save()
    
    return {"status": "success", "message": f"Team '{original_name}' has been deleted"}


def archive_team(team_id):
    """Archive a team."""
    team = get_object_or_404(TeamOrganization, pk=team_id)
    team.is_archived = True
    team.save()
    
    return {"status": "success", "team": team, "message": f"Team '{team.name}' archived"}


def unarchive_team(team_id):
    """Unarchive a team."""
    team = get_object_or_404(TeamOrganization, pk=team_id)
    team.is_archived = False
    team.save()
    
    return {"status": "success", "team": team, "message": f"Team '{team.name}' unarchived"}


def get_team_history(team_id):
    """Get the participation history of a team across seasons."""
    team = get_object_or_404(TeamOrganization, pk=team_id)
    
    participations = SeasonTeam.objects.filter(
        team=team,
        season__is_deleted=False  # Explicitly exclude deleted seasons
    ).select_related(
        'season', 'level'
    ).order_by('-season__created_at')
    
    history = []
    for participation in participations:
        history.append({
            'season_id': participation.season.id,
            'season_name': participation.season.name,
            'level_name': participation.level.name,
            'is_active_season': participation.season.is_active
        })
    
    return {"status": "success", "team": team, "history": history}


def get_available_teams_for_season(season_id):
    """Get teams that are available to be assigned to a season."""
    season = get_object_or_404(Season, pk=season_id)
    
    # Get teams that are not archived and not already assigned to this season
    assigned_team_ids = SeasonTeam.objects.filter(season=season).values_list('team_id', flat=True)
    available_teams = TeamOrganization.objects.filter(
        is_archived=False
    ).exclude(id__in=assigned_team_ids).order_by('name')
    
    return available_teams


def assign_teams_to_season(season_id, team_assignments):
    """
    Assign teams to a season with level assignments.
    
    team_assignments is a list of dicts: [{'team_id': int, 'level_id': int}, ...]
    """
    season = get_object_or_404(Season, pk=season_id)
    
    with transaction.atomic():
        created_assignments = []
        errors = []
        
        for assignment in team_assignments:
            team_id = assignment.get('team_id')
            level_id = assignment.get('level_id')
            
            try:
                team = TeamOrganization.objects.get(pk=team_id)
                level = Level.objects.get(pk=level_id, season=season)
                
                # Check if team is already assigned to this season
                if SeasonTeam.objects.filter(season=season, team=team).exists():
                    errors.append(f"Team '{team.name}' is already assigned to this season")
                    continue
                
                # Check if another team with the same name is already in this season
                if SeasonTeam.objects.filter(season=season, team__name=team.name).exists():
                    errors.append(f"A team named '{team.name}' is already assigned to this season")
                    continue
                
                season_team = SeasonTeam.objects.create(
                    season=season,
                    team=team,
                    level=level
                )
                created_assignments.append(season_team)
                
            except TeamOrganization.DoesNotExist:
                errors.append(f"Team with ID {team_id} not found")
            except Level.DoesNotExist:
                errors.append(f"Level with ID {level_id} not found for this season")
    
    return {
        "status": "success" if not errors else "partial_success",
        "created": len(created_assignments),
        "errors": errors,
        "message": f"Assigned {len(created_assignments)} teams to season"
    }


def update_team_level_assignments(season_id, level_assignments):
    """
    Update level assignments for teams in a season.
    
    level_assignments is a list of dicts: [{'season_team_id': int, 'level_id': int}, ...]
    """
    season = get_object_or_404(Season, pk=season_id)
    
    with transaction.atomic():
        updated_count = 0
        errors = []
        
        for assignment in level_assignments:
            season_team_id = assignment.get('season_team_id')
            level_id = assignment.get('level_id')
            
            try:
                season_team = SeasonTeam.objects.get(pk=season_team_id, season=season)
                level = Level.objects.get(pk=level_id, season=season)
                
                season_team.level = level
                season_team.save()
                updated_count += 1
                
            except SeasonTeam.DoesNotExist:
                errors.append(f"Season team assignment with ID {season_team_id} not found")
            except Level.DoesNotExist:
                errors.append(f"Level with ID {level_id} not found for this season")
    
    return {
        "status": "success" if not errors else "partial_success",
        "updated": updated_count,
        "errors": errors,
        "message": f"Updated {updated_count} team level assignments"
    }


def remove_teams_from_season(season_id, team_ids):
    """Remove teams from a season (if they don't have games)."""
    season = get_object_or_404(Season, pk=season_id)
    
    with transaction.atomic():
        removed_count = 0
        errors = []
        
        for team_id in team_ids:
            try:
                team = TeamOrganization.objects.get(pk=team_id)
                season_team = SeasonTeam.objects.get(season=season, team=team)
                
                # Check if this team has any games in this season
                from scheduler.models import Game
                has_games = Game.objects.filter(
                    Q(season_team1=season_team) | 
                    Q(season_team2=season_team) | 
                    Q(referee_season_team=season_team)
                ).exists()
                
                if has_games:
                    errors.append(f"Cannot remove team '{team.name}' - it has scheduled games")
                    continue
                
                season_team.delete()
                removed_count += 1
                
            except TeamOrganization.DoesNotExist:
                errors.append(f"Team with ID {team_id} not found")
            except SeasonTeam.DoesNotExist:
                errors.append(f"Team with ID {team_id} is not assigned to this season")
    
    return {
        "status": "success" if not errors else "partial_success",
        "removed": removed_count,
        "errors": errors,
        "message": f"Removed {removed_count} teams from season"
    }