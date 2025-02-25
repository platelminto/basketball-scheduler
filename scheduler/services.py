from django.db import models, transaction
from scheduler.models import Game, Team


def update_game_score(game_id, team1_score, team2_score):
    """
    Update a game's score and recalculate team statistics.

    Args:
        game_id (int): The ID of the game to update
        team1_score (int): Score for team1
        team2_score (int): Score for team2

    Returns:
        Game: The updated game object

    Raises:
        Game.DoesNotExist: If no game with the given ID exists
    """
    with transaction.atomic():
        game = Game.objects.select_related("team1", "team2").get(pk=game_id)
        game.team1_score = team1_score
        game.team2_score = team2_score
        game.save()  # This will trigger the update_team_stats method
        return game


def get_standings(level_id=None):
    """
    Get team standings, optionally filtered by level.

    Args:
        level_id (int, optional): Filter teams by level ID

    Returns:
        QuerySet: Teams ordered by wins (desc), point_differential (desc)
    """
    teams = Team.objects.all()

    if level_id:
        teams = teams.filter(level_id=level_id)

    return teams.order_by("-wins", "-point_differential")


def get_games_for_week(week_number, level_id=None):
    """
    Get all games for a specific week, optionally filtered by level.

    Args:
        week_number (int): The week number
        level_id (int, optional): Filter games by level ID

    Returns:
        QuerySet: Games for the specified week
    """
    games = Game.objects.filter(week=week_number)

    if level_id:
        games = games.filter(level_id=level_id)

    return games.order_by("start_time")


def get_team_schedule(team_id):
    """
    Get all games for a specific team.

    Args:
        team_id (int): The team ID

    Returns:
        QuerySet: Games where the team is playing
    """
    return Game.objects.filter(
        models.Q(team1_id=team_id) | models.Q(team2_id=team_id)
    ).order_by("week", "start_time")


def get_referee_schedule(team_id):
    """
    Get all games where a team is refereeing.

    Args:
        team_id (int): The team ID

    Returns:
        QuerySet: Games where the team is refereeing
    """
    return Game.objects.filter(referee_id=team_id).order_by("week", "start_time")
