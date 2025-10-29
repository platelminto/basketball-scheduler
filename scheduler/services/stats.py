"""
Statistics calculation service functions.

This module provides centralized calculation of team and season statistics,
as well as schedule balance and distribution statistics.
"""

import math
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


def get_head_to_head_winner(season_team1_id, season_team2_id):
    """
    Compare head-to-head record between two season teams.
    Returns: 1 if team1 wins more H2H, -1 if team2 wins more, 0 if tied.
    """
    # Get all completed games between these two teams
    games_team1_home = Game.objects.filter(
        season_team1_id=season_team1_id,
        season_team2_id=season_team2_id,
        team1_score__isnull=False,
        team2_score__isnull=False
    )

    games_team1_away = Game.objects.filter(
        season_team1_id=season_team2_id,
        season_team2_id=season_team1_id,
        team1_score__isnull=False,
        team2_score__isnull=False
    )

    team1_wins = 0
    team2_wins = 0

    # Count wins when team1 is home
    for game in games_team1_home:
        if game.team1_score > game.team2_score:
            team1_wins += 1
        elif game.team2_score > game.team1_score:
            team2_wins += 1

    # Count wins when team1 is away
    for game in games_team1_away:
        if game.team2_score > game.team1_score:
            team1_wins += 1
        elif game.team1_score > game.team2_score:
            team2_wins += 1

    if team1_wins > team2_wins:
        return 1
    elif team2_wins > team1_wins:
        return -1
    else:
        return 0


def _apply_head_to_head_tiebreaker(teams):
    """
    Apply head-to-head tiebreaker to a list of teams from the same level.
    Teams should already be sorted by PCT, PD, PA.
    """
    if len(teams) <= 1:
        return teams

    # Group teams by their current standing (PCT, PD, PA)
    tie_groups = []
    current_group = [teams[0]]

    for i in range(1, len(teams)):
        prev_team = teams[i-1]
        curr_team = teams[i]

        # Check if teams are tied on PCT, PD, and PA
        if (prev_team['win_pct'] == curr_team['win_pct'] and
            prev_team['point_diff'] == curr_team['point_diff'] and
            prev_team['points_against'] == curr_team['points_against']):
            current_group.append(curr_team)
        else:
            tie_groups.append(current_group)
            current_group = [curr_team]

    tie_groups.append(current_group)

    # Apply H2H tiebreaker within each tied group
    result = []
    for group in tie_groups:
        if len(group) == 2:
            # For exactly 2 teams, use H2H directly
            team1, team2 = group
            h2h_result = get_head_to_head_winner(team1['season_team_id'], team2['season_team_id'])
            if h2h_result == 1:
                result.extend([team1, team2])
            elif h2h_result == -1:
                result.extend([team2, team1])
            else:
                # H2H is tied, keep original order
                result.extend(group)
        else:
            # For 3+ teams or single teams, keep original order
            # (Could implement round-robin H2H comparison here if needed)
            result.extend(group)

    return result


def calculate_season_standings(season):
    """Calculate standings for all teams in a season."""
    season_teams = SeasonTeam.objects.filter(season=season).select_related('team', 'level')

    standings = []
    for season_team in season_teams:
        team_stats = calculate_team_stats_in_season(season_team)
        standings.append(team_stats)

    # Sort standings by level, then by wins, then by draws, then by point differential, then by points against
    standings.sort(key=lambda x: (
        x['level_id'],
        -x['wins'],  # More wins first
        -x['draws'],  # More draws second (fewer losses)
        -x['point_diff'],  # Better point differential third
        x['points_against']  # Lower points against fourth
    ))

    # Apply head-to-head tiebreaker as final step
    # Group teams by level and apply H2H within each level
    final_standings = []
    current_level = None
    level_teams = []

    for team in standings:
        if team['level_id'] != current_level:
            # Process previous level's teams with H2H tiebreaker
            if level_teams:
                final_standings.extend(_apply_head_to_head_tiebreaker(level_teams))
            # Start new level
            current_level = team['level_id']
            level_teams = [team]
        else:
            level_teams.append(team)

    # Process final level
    if level_teams:
        final_standings.extend(_apply_head_to_head_tiebreaker(level_teams))

    standings = final_standings
    
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


# Schedule Statistics Functions

def compute_games_per_slot(schedule, levels):
    """
    Compute the number of games per slot for each level.

    Args:
        schedule: The formatted schedule data (list of weeks with slots)
        levels: List of competition levels (e.g., ["A", "B", "C"])

    Returns:
        dict: Dictionary mapping levels to slots to game counts
    """
    # Determine max slot number from schedule
    max_slot = 1
    for week in schedule:
        for slot_key in week["slots"].keys():
            max_slot = max(max_slot, int(slot_key))
    
    counts = {level: {s: 0 for s in range(1, max_slot + 1)} for level in levels}

    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in levels:
                    counts[level][slot] += 1

    return counts


def compute_team_play_counts(schedule, teams_per_level):
    """
    Compute how many times each team plays in each slot.
    
    Args:
        schedule: The formatted schedule data
        team_names_by_level: Dict mapping level to list of team names
        levels: List of competition levels
        
    Returns:
        dict: Nested dict {level: {team_name: {slot: count}}}
    """
    # Determine max slot number from schedule
    max_slot = 1
    for week in schedule:
        for slot_key in week["slots"].keys():
            max_slot = max(max_slot, int(slot_key))

    # Initialize counts with team names
    counts = {}
    for level in teams_per_level:
        counts[level] = {}
        for team_name in teams_per_level.get(level, []):
            counts[level][team_name] = {s: 0 for s in range(1, max_slot + 1)}

    # Count team appearances in each slot
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in teams_per_level and level in counts:
                    for team_name in game["teams"]:
                        if team_name in counts[level]:
                            counts[level][team_name][slot] += 1

    return counts


def compute_team_ref_counts(schedule, teams_per_level):
    """
    Compute how many times each team referees in each slot.
    
    Args:
        schedule: The formatted schedule data
        teams_per_level: Dict mapping level to list of team names
        levels: List of competition levels
        
    Returns:
        dict: Nested dict {level: {team_name: {slot: count}}}
    """
    # Determine max slot number from schedule
    max_slot = 1
    for week in schedule:
        for slot_key in week["slots"].keys():
            max_slot = max(max_slot, int(slot_key))

    # Initialize counts with team names
    counts = {}
    for level in teams_per_level:
        counts[level] = {}
        for team_name in teams_per_level.get(level, []):
            counts[level][team_name] = {s: 0 for s in range(1, max_slot + 1)}

    # Count referee assignments in each slot (only for teams in that level)
    for week in schedule:
        for slot_key, games in week["slots"].items():
            slot = int(slot_key)
            for game in games:
                level = game["level"]
                if level in teams_per_level and level in counts:
                    ref_name = game.get("ref", "")
                    # Only count if the referee is actually a team in this level
                    if ref_name and ref_name in teams_per_level[level] and ref_name in counts[level]:
                        counts[level][ref_name][slot] += 1

    return counts


def compute_overall_ref_counts(schedule, teams_per_level):
    """
    Compute total times each team referees across all slots.
    
    Args:
        schedule: The formatted schedule data
        teams_per_level: Dict mapping level to list of team names
        levels: List of competition levels
        
    Returns:
        dict: {level: {team_name: total_ref_count}}
    """
    counts = {}
    for level in teams_per_level:
        counts[level] = {}
        for team_name in teams_per_level.get(level, []):
            counts[level][team_name] = 0

    for week in schedule:
        for _, games in week["slots"].items():
            for game in games:
                level = game["level"]
                if level in teams_per_level and level in counts:
                    ref_name = game.get("ref", "")
                    # Only count if the referee is actually a team in this level
                    if ref_name and ref_name in teams_per_level[level] and ref_name in counts[level]:
                        counts[level][ref_name] += 1

    return counts


def compute_balance_metrics(play_counts, ref_counts):
    """
    Compute balance and fairness metrics for the schedule.
    
    Args:
        play_counts: Team play counts by slot
        ref_counts: Team referee counts by slot
        
    Returns:
        dict: Balance metrics including standard deviations and ranges
    """
    metrics = {}
    
    for level in play_counts.keys():
        level_metrics = {
            "play_balance": {},
            "ref_balance": {},
            "overall_balance": {}
        }
        
        # Determine max slot number
        max_slot = 1
        for team_counts in play_counts[level].values():
            if team_counts:
                max_slot = max(max_slot, max(team_counts.keys()))
        
        # Compute play balance per slot
        for slot in range(1, max_slot + 1):
            if any(slot in team_counts for team_counts in play_counts[level].values()):
                slot_plays = [team_counts.get(slot, 0) for team_counts in play_counts[level].values()]
                if slot_plays:
                    avg = sum(slot_plays) / len(slot_plays)
                    level_metrics["play_balance"][f"slot_{slot}"] = {
                        "min": min(slot_plays),
                        "max": max(slot_plays),
                        "avg": avg,
                        "std_dev": math.sqrt(sum((x - avg)**2 for x in slot_plays) / len(slot_plays)) if len(slot_plays) > 1 else 0
                    }
        
        # Compute referee balance per slot
        for slot in range(1, max_slot + 1):
            if any(slot in team_counts for team_counts in ref_counts[level].values()):
                slot_refs = [team_counts.get(slot, 0) for team_counts in ref_counts[level].values()]
                if slot_refs:
                    avg = sum(slot_refs) / len(slot_refs)
                    level_metrics["ref_balance"][f"slot_{slot}"] = {
                        "min": min(slot_refs),
                        "max": max(slot_refs),
                        "avg": avg,
                        "std_dev": math.sqrt(sum((x - avg)**2 for x in slot_refs) / len(slot_refs)) if len(slot_refs) > 1 else 0
                    }
        
        # Compute overall balance (total plays per team)
        total_plays = [sum(team_counts.values()) for team_counts in play_counts[level].values()]
        if total_plays:
            avg = sum(total_plays) / len(total_plays)
            level_metrics["overall_balance"]["plays"] = {
                "min": min(total_plays),
                "max": max(total_plays),
                "avg": avg,
                "std_dev": math.sqrt(sum((x - avg)**2 for x in total_plays) / len(total_plays)) if len(total_plays) > 1 else 0
            }
        
        total_refs = [sum(team_counts.values()) for team_counts in ref_counts[level].values()]
        if total_refs:
            avg = sum(total_refs) / len(total_refs)
            level_metrics["overall_balance"]["refs"] = {
                "min": min(total_refs),
                "max": max(total_refs),
                "avg": avg,
                "std_dev": math.sqrt(sum((x - avg)**2 for x in total_refs) / len(total_refs)) if len(total_refs) > 1 else 0
            }
        
        metrics[level] = level_metrics
    
    return metrics


def compute_schedule_statistics(schedule_data, teams_per_level):
    """
    Compute comprehensive statistics for a schedule.
    
    Args:
        schedule_data: The formatted schedule data
        teams_per_level: The names of teams organized by level

    Returns:
        dict: Complete statistics including game distribution, team balance, and metrics
    """
    
    # Compute all statistics
    games_per_slot = compute_games_per_slot(schedule_data, list(teams_per_level.keys()))
    play_counts = compute_team_play_counts(schedule_data, teams_per_level)
    ref_counts = compute_team_ref_counts(schedule_data, teams_per_level)
    overall_ref_counts = compute_overall_ref_counts(schedule_data, teams_per_level)
    balance_metrics = compute_balance_metrics(play_counts, ref_counts)
    
    return {
        "games_per_slot": games_per_slot,
        "team_play_counts": play_counts,
        "team_ref_counts": ref_counts,
        "overall_ref_counts": overall_ref_counts,
        "balance_metrics": balance_metrics,
        "summary": {
            "total_games": sum(
                sum(level_counts.values()) 
                for level_counts in games_per_slot.values()
            ),
            "teams_per_level": teams_per_level,
        }
    }