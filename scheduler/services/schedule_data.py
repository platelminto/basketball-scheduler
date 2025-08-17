"""
Schedule data retrieval service functions.

This module contains business logic for retrieving and formatting
schedule data for API endpoints.
"""

from scheduler.models import Season, Week, OffWeek, Game, Level, Team


def get_teams_and_levels_data(season):
    """Get all levels and teams data for a season."""
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

    return levels_data, teams_by_level


def format_games_by_week(all_week_data):
    """Format games data organized by week."""
    games_by_week = {}
    
    for week_num, week_data in enumerate(all_week_data, 1):
        if week_data["type"] == "regular":
            week = week_data["week_obj"]
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
            off_week = week_data["week_obj"]
            games_by_week[week_num] = {
                "id": f"off_{off_week.id}",
                "week_number": week_num,
                "monday_date": off_week.monday_date.strftime("%Y-%m-%d"),
                "isOffWeek": True,
                "title": off_week.title,
                "description": off_week.description,
                "has_basketball": off_week.has_basketball,
                "start_time": off_week.start_time.strftime("%H:%M") if off_week.start_time else None,
                "end_time": off_week.end_time.strftime("%H:%M") if off_week.end_time else None,
                "games": [],
            }

    return games_by_week


def get_schedule_data_for_season(season):
    """Get comprehensive schedule data for a season."""
    # Get all weeks in this season (both regular and off weeks)
    weeks = Week.objects.filter(season=season).order_by("week_number")
    off_weeks = OffWeek.objects.filter(season=season).order_by("monday_date")

    # Create a combined list of all weeks (regular and off) sorted by date
    all_week_data = []

    # Add regular weeks
    for week in weeks:
        all_week_data.append(
            {
                "type": "regular",
                "date": week.monday_date,
                "week_obj": week,
            }
        )

    # Add off weeks
    for off_week in off_weeks:
        all_week_data.append(
            {
                "type": "off",
                "date": off_week.monday_date,
                "week_obj": off_week,
            }
        )

    # Sort all weeks by date
    all_week_data.sort(key=lambda x: x["date"])

    # Process weeks and format games
    games_by_week = format_games_by_week(all_week_data)

    # Get levels and teams data
    levels_data, teams_by_level = get_teams_and_levels_data(season)

    # Get all courts
    courts = list(
        Game.objects.filter(level__season=season)
        .values_list("court", flat=True)
        .distinct()
        .order_by("court")
    )
    courts = [court for court in courts if court]

    return {
        "season": {
            "id": season.id,
            "name": season.name,
        },
        "weeks": games_by_week,
        "levels": levels_data,
        "teams_by_level": teams_by_level,
        "courts": courts,
    }


def get_public_schedule_data():
    """Get schedule data for the currently active season."""
    # Get the active season
    active_season = Season.objects.filter(is_active=True).first()
    if not active_season:
        raise ValueError("No active season found")

    return get_schedule_data_for_season(active_season)