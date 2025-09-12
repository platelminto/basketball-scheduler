"""
Calendar export service functions.

This module contains business logic for generating iCal calendar files
for team schedules including games and tournaments.
"""

from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from icalendar import Calendar, Event
from scheduler.models import TeamOrganization, SeasonTeam, Game, OffWeek, Season


def handle_calendar_options(request):
    """Parse query parameters for calendar generation options."""
    include_reffing = request.GET.get("include_reffing", "false").lower() == "true"
    include_scores = request.GET.get("include_scores", "false").lower() == "true"
    include_tournaments = request.GET.get("include_tournaments", "false").lower() == "true"
    
    return include_reffing, include_scores, include_tournaments


def format_game_title(game, team, include_scores):
    """Format the title for a game event."""
    if game.season_team1.team == team or game.season_team2.team == team:
        # Playing game - respect team1 vs team2 order
        title = f"{game.season_team1.team.name} vs {game.season_team2.team.name}"

        # Add winner indicator to title if game is completed and scores are requested
        if (
            include_scores
            and game.team1_score is not None
            and game.team2_score is not None
        ):
            if game.team1_score > game.team2_score:
                title = f"{game.season_team1.team.name} (W) vs {game.season_team2.team.name} (L)"
            elif game.team2_score > game.team1_score:
                title = f"{game.season_team1.team.name} (L) vs {game.season_team2.team.name} (W)"
            # If tied, leave title as is

        return title, "Playing"
    else:
        # Reffing game - shortened format
        title = f"Ref: {game.season_team1.team.name} vs {game.season_team2.team.name}"

        # Add winner indicator to title if game is completed and scores are requested
        if (
            include_scores
            and game.team1_score is not None
            and game.team2_score is not None
        ):
            if game.team1_score > game.team2_score:
                title = f"Ref: {game.season_team1.team.name} (W) vs {game.season_team2.team.name} (L)"
            elif game.team2_score > game.team1_score:
                title = f"Ref: {game.season_team1.team.name} (L) vs {game.season_team2.team.name} (W)"
            # If tied, leave title as is

        return title, "Reffing"


def format_game_description(game, include_scores):
    """Format the description for a game event."""
    description_parts = [f"• Level: {game.level.name}"]

    if game.referee_season_team:
        description_parts.append(f"• Referee: {game.referee_season_team.team.name}")
    elif game.referee_name:
        description_parts.append(f"• Referee: {game.referee_name}")

    # Add scores if game is completed and scores are requested
    if (
        include_scores
        and game.team1_score is not None
        and game.team2_score is not None
    ):
        score_line = f"• Final Score: {game.season_team1.team.name} {game.team1_score} - {game.team2_score} {game.season_team2.team.name}"
        description_parts.append(score_line)

    return "\n".join(description_parts)


def format_calendar_events(games, team, include_scores):
    """Format game events for calendar."""
    events = []
    
    for game in games:
        event = Event()

        # Determine event type and title
        title, category = format_game_title(game, team, include_scores)
        event.add("summary", title)
        event.add("categories", category)

        # Calculate datetime
        if game.date_time:
            start_time = game.date_time
            # Use level's slot duration for event duration
            duration = game.level.get_effective_slot_duration()
            end_time = start_time + timedelta(minutes=duration)

            event.add("dtstart", start_time)
            event.add("dtend", end_time)

        # Add location
        if game.court:
            event.add("location", game.court)

        # Build description
        description = format_game_description(game, include_scores)
        event.add("description", description)

        # Add unique ID
        event.add("uid", f"game-{game.id}@basketballscheduler.local")

        # Add creation timestamp
        event.add("dtstamp", timezone.now())

        events.append(event)

    return events


def format_tournament_events(off_weeks):
    """Format off-week/tournament events for calendar."""
    events = []
    
    for off_week in off_weeks:
        # Only include off-weeks that have both start and end times
        if off_week.start_time and off_week.end_time:
            event = Event()
            
            # Create title - use description or title, no "Tournament:" prefix
            if off_week.description:
                title = off_week.description
            else:
                title = off_week.title or "Event"
            
            event.add("summary", title)
            event.add("categories", "Event")
            
            # Calculate datetime - combine date with start/end times
            start_datetime = datetime.combine(off_week.monday_date, off_week.start_time)
            end_datetime = datetime.combine(off_week.monday_date, off_week.end_time)
            
            event.add("dtstart", start_datetime)
            event.add("dtend", end_datetime)
            
            # Add description - same as title
            event.add("description", title)
            
            # Add unique ID
            event.add("uid", f"offweek-{off_week.id}@basketballscheduler.local")
            
            # Add creation timestamp
            event.add("dtstamp", timezone.now())
            
            events.append(event)

    return events


def generate_team_calendar(team_org_id, include_reffing, include_scores, include_tournaments):
    """Generate iCal calendar for a team organization's schedule across all seasons."""
    team_org = get_object_or_404(TeamOrganization, pk=team_org_id)

    # Create calendar
    cal = Calendar()
    cal.add("prodid", "-//Basketball Scheduler//Team Calendar//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"{team_org.name}")
    cal.add("x-wr-caldesc", f"USBF schedule for {team_org.name}")
    cal.add("name", f"{team_org.name}")
    cal.add("x-wr-timezone", "Europe/Amsterdam")
    cal.add("displayname", f"{team_org.name}")
    cal.add("x-apple-calendar-color", "#3b82f6")

    # Query for games across all seasons for this team organization
    games_query = Q(season_team1__team=team_org) | Q(season_team2__team=team_org)
    if include_reffing:
        games_query |= Q(referee_season_team__team=team_org)

    games = (
        Game.objects.filter(games_query)
        .select_related("level", "season_team1__team", "season_team2__team", "referee_season_team__team", "week")
        .order_by("week__monday_date", "day_of_week", "time")
    )

    # Format and add game events
    game_events = format_calendar_events(games, team_org, include_scores)
    for event in game_events:
        cal.add_component(event)

    # Add off-weeks/tournaments if requested
    if include_tournaments:
        # Get all seasons this team has participated in (managers automatically filter deleted seasons)
        seasons = Season.objects.filter(
            levels__season_teams__team=team_org
        ).distinct()
        
        for season in seasons:
            off_weeks = OffWeek.objects.filter(season=season).select_related("season")
            tournament_events = format_tournament_events(off_weeks)
            for event in tournament_events:
                cal.add_component(event)

    return cal, team_org