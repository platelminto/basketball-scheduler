"""
Statistics calculation service functions.

This module provides centralized calculation of team and season statistics,
avoiding duplication between frontend and backend calculations.
"""

from django.db.models import Q
from scheduler.models import Game, SeasonTeam, Season, TeamOrganization


def is_game_completed(game):
    """Check if a game has been completed (both scores entered)."""
    return game.team1_score is not None and game.team2_score is not None


def calculate_team_stats_in_season(season_team):
    """Calculate stats for a specific team in a specific season."""
    # Get all games for this season team
    games_as_team1 = Game.objects.filter(season_team1=season_team)
    games_as_team2 = Game.objects.filter(season_team2=season_team)
    
    stats = {
        'season_team_id': season_team.id,
        'team_id': season_team.team.id,
        'team_name': season_team.team.name,
        'season_id': season_team.season.id,
        'season_name': season_team.season.name,
        'level_id': season_team.level.id,
        'level_name': season_team.level.name,
        'games_played': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'points_for': 0,
        'points_against': 0,
        'win_pct': 0.0,
        'point_diff': 0,
        'final_position': None
    }
    
    # Process games as team1
    for game in games_as_team1:
        if is_game_completed(game):
            stats['games_played'] += 1
            stats['points_for'] += game.team1_score
            stats['points_against'] += game.team2_score
            
            if game.team1_score > game.team2_score:
                stats['wins'] += 1
            elif game.team1_score < game.team2_score:
                stats['losses'] += 1
            else:
                stats['draws'] += 1
    
    # Process games as team2
    for game in games_as_team2:
        if is_game_completed(game):
            stats['games_played'] += 1
            stats['points_for'] += game.team2_score
            stats['points_against'] += game.team1_score
            
            if game.team2_score > game.team1_score:
                stats['wins'] += 1
            elif game.team2_score < game.team1_score:
                stats['losses'] += 1
            else:
                stats['draws'] += 1
    
    # Calculate derived stats
    if stats['games_played'] > 0:
        stats['win_pct'] = stats['wins'] / stats['games_played']
    stats['point_diff'] = stats['points_for'] - stats['points_against']
    
    return stats


def calculate_season_standings(season):
    """Calculate standings for all teams in a season."""
    season_teams = SeasonTeam.objects.filter(season=season).select_related('team', 'level')
    
    standings = []
    for season_team in season_teams:
        team_stats = calculate_team_stats_in_season(season_team)
        standings.append(team_stats)
    
    # Sort standings by level, then by win percentage, then by point differential
    standings.sort(key=lambda x: (
        x['level_id'],
        -x['win_pct'],  # Higher win percentage first
        -x['point_diff'],  # Better point differential first
        x['points_against']  # Lower points against as tiebreaker
    ))
    
    # Calculate final positions within each level
    current_level = None
    position = 1
    for i, team in enumerate(standings):
        if team['level_id'] != current_level:
            current_level = team['level_id']
            position = 1
        else:
            position += 1
        team['final_position'] = position
    
    return standings


def get_team_history_stats(team_organization):
    """Get comprehensive stats for a team across all seasons."""
    season_teams = SeasonTeam.objects.filter(
        team=team_organization,
        season__is_deleted=False  # Explicitly exclude deleted seasons
    ).select_related('season', 'level').order_by('-season__created_at')
    
    seasons_stats = []
    for season_team in season_teams:
        team_stats = calculate_team_stats_in_season(season_team)
        
        # Calculate final position by getting full standings for this season
        season_standings = calculate_season_standings(season_team.season)
        for standing in season_standings:
            if standing['season_team_id'] == season_team.id:
                team_stats['final_position'] = standing['final_position']
                break
        
        seasons_stats.append(team_stats)
    
    return {
        'team_id': team_organization.id,
        'team_name': team_organization.name,
        'seasons': seasons_stats
    }


def get_team_history_with_league_tables(team_organization):
    """Get team history with league table data for each season."""
    season_teams = SeasonTeam.objects.filter(
        team=team_organization,
        season__is_deleted=False  # Explicitly exclude deleted seasons
    ).select_related('season', 'level').order_by('-season__created_at')
    
    seasons_data = []
    for season_team in season_teams:
        # Get all standings for this season
        season_standings = calculate_season_standings(season_team.season)
        
        # Filter standings to only include teams from the same level
        level_standings = [
            standing for standing in season_standings 
            if standing['level_id'] == season_team.level.id
        ]
        
        # Transform standings to match frontend StandingsTable format
        transformed_standings = []
        for standing in level_standings:
            transformed_standings.append({
                'id': standing['team_id'],
                'name': standing['team_name'],
                'level_id': standing['level_id'],
                'level_name': standing['level_name'],
                'gamesPlayed': standing['games_played'],
                'wins': standing['wins'],
                'losses': standing['losses'],
                'draws': standing['draws'],
                'pointsFor': standing['points_for'],
                'pointsAgainst': standing['points_against'],
                'winPct': standing['win_pct'],
                'pointDiff': standing['point_diff'],
                'position': standing['final_position']
            })
        
        seasons_data.append({
            'season_id': season_team.season.id,
            'season_name': season_team.season.name,
            'level_id': season_team.level.id,
            'level_name': season_team.level.name,
            'standings': transformed_standings,
            'levels': [{
                'id': season_team.level.id,
                'name': season_team.level.name
            }]
        })
    
    return {
        'team_id': team_organization.id,
        'team_name': team_organization.name,
        'seasons': seasons_data
    }


def get_team_current_season_stats(team_organization):
    """Get stats for a team in the current active season only."""
    try:
        active_season = Season.objects.get(is_active=True)
        season_team = SeasonTeam.objects.get(
            team=team_organization, 
            season=active_season
        )
        return calculate_team_stats_in_season(season_team)
    except (Season.DoesNotExist, SeasonTeam.DoesNotExist):
        return None