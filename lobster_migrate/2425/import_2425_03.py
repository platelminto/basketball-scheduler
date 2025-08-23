#!/usr/bin/env python3
"""
Simple parser that follows the exact format:
Time -> Level -> Referee -> Team1 -> Score -> Team2
"""

import os
import sys
import django
from datetime import datetime
import re

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'league_manager.settings')
django.setup()

from scheduler.models import Season, Level, TeamOrganization, SeasonTeam, Week, OffWeek, Game


def parse_schedule_simple(filename):
    """Parse following exact format: time, level, ref, team1, score, team2"""
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines()]
    
    # Skip to schedule section (after standings)
    start_idx = 0
    for i, line in enumerate(lines):
        if 'Week 1' in line and i > 40:
            start_idx = i
            break
    
    # Extract teams from standings first
    teams_by_level = {}
    current_level = None
    
    for i, line in enumerate(lines[:start_idx]):
        if line in ['Top', 'High', 'Mid']:
            current_level = line
            teams_by_level[current_level] = []
            continue
        
        if current_level and line:
            parts = line.split('\t')
            if len(parts) >= 9 and parts[0].strip().isdigit():
                team_name = parts[1].strip()
                if team_name:
                    teams_by_level[current_level].append(team_name)
    
    print(f"Teams: {teams_by_level}")
    
    # Parse schedule
    games = []
    current_week = None
    current_date = None
    off_weeks = []
    off_week_count = 0  # Track how many off-weeks we've seen
    
    i = start_idx
    while i < len(lines):
        line = lines[i]
        
        # Week header
        if line.startswith('Week '):
            week_num = int(re.search(r'Week (\d+)', line).group(1))
            # Real week number = file week number + off-weeks encountered so far
            current_week = week_num + off_week_count
            print(f"Week {week_num} -> Week {current_week} (after {off_week_count} off-weeks)")
            i += 1
            continue
            
        # Date
        if re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ', line):
            date_str = line.split(', ')[1]
            year = 2025  # All dates are 2025
            current_date = datetime.strptime(f"{date_str} {year}", "%B %d %Y").date()
            i += 1
            continue
            
        # Off week
        if line == 'Off-Week':
            if current_date:
                # Off weeks should be sequential weeks after the current date
                from datetime import timedelta
                off_week_date = current_date + timedelta(days=7)
                off_weeks.append({'week': None, 'date': off_week_date})
                off_week_count += 1
                print(f"Found off-week #{off_week_count} on {off_week_date}")
                
                # Check for consecutive Off-Week lines
                j = i + 1
                while j < len(lines) and lines[j].strip() == 'Off-Week':
                    off_week_date = off_week_date + timedelta(days=7)
                    off_weeks.append({'week': None, 'date': off_week_date})
                    off_week_count += 1
                    print(f"Found off-week #{off_week_count} on {off_week_date}")
                    j += 1
                i = j - 1  # Set i to the last Off-Week line processed
            i += 1
            continue
            
        # Time (start of game)
        if re.match(r'\d{2}:\d{2}', line) and i + 4 < len(lines):
            time_str = line
            level = lines[i + 1]
            
            # Check if next line is a score (no referee case)
            if re.search(r'\d+\s*:\s*\d+', lines[i + 3]):
                # Format: Time -> Level -> Team1 -> Score -> Team2
                referee = ""
                team1 = lines[i + 2]
                score_line = lines[i + 3]
                team2 = lines[i + 4] if i + 4 < len(lines) else ""
                skip_lines = 5
            else:
                # Format: Time -> Level -> Referee -> [Match menu] -> Team1 -> Score -> Team2
                if i + 6 >= len(lines):
                    i += 1
                    continue
                referee = lines[i + 2]
                # Skip "Match menu" if present
                if lines[i + 3] == "Match menu":
                    team1 = lines[i + 4]
                    score_line = lines[i + 5]
                    team2 = lines[i + 6]
                    skip_lines = 7
                else:
                    team1 = lines[i + 3]
                    score_line = lines[i + 4]
                    team2 = lines[i + 5]
                    skip_lines = 6
            
            # Parse score
            score_match = re.search(r'(\d+)\s*:\s*(\d+)', score_line)
            if score_match and level in ['Top', 'High', 'Mid'] and team1 and team2:
                team1_score = int(score_match.group(1))
                team2_score = int(score_match.group(2))
                
                games.append({
                    'week': current_week,
                    'date': current_date,
                    'time': time_str,
                    'level': level,
                    'referee': referee,
                    'team1': team1,
                    'team2': team2,
                    'team1_score': team1_score,
                    'team2_score': team2_score
                })
                ref_str = f"ref:{referee}" if referee else "no ref"
                print(f"Game {len(games)}: {time_str} {level} {team1} vs {team2} ({team1_score}-{team2_score}) {ref_str}")
            else:
                print(f"FAILED to parse game at line {i}: time={time_str} level={level} team1={team1} score={score_line} team2={team2}")
            
            i += skip_lines
            continue
            
        i += 1
    
    print(f"Parsed {len(games)} games and {len(off_weeks)} off weeks")
    return teams_by_level, games, off_weeks


def import_data(filename):
    teams_by_level, games, off_weeks = parse_schedule_simple(filename)
    
    # Create season
    season, created = Season.objects.get_or_create(
        name="USBF '24-'25, Season 3",
        defaults={'is_active': False, 'slot_duration_minutes': 70}
    )
    
    # Create levels
    levels = {}
    for level_name in ['Top', 'High', 'Mid']:
        level, created = Level.objects.get_or_create(
            season=season, name=level_name
        )
        levels[level_name] = level
    
    # Create teams and season teams
    all_teams = set()
    for level_teams in teams_by_level.values():
        all_teams.update(level_teams)
    
    season_teams = {}
    for team_name in all_teams:
        # Find level
        team_level = None
        for level_name, team_names in teams_by_level.items():
            if team_name in team_names:
                team_level = level_name
                break
        
        if team_level:
            team_org, created = TeamOrganization.objects.get_or_create(
                name=team_name,
                defaults={'is_archived': False, 'is_deleted': False}
            )
            season_team, created = SeasonTeam.objects.get_or_create(
                season=season, team=team_org,
                defaults={'level': levels[team_level]}
            )
            season_teams[team_name] = season_team
    
    # Create weeks
    weeks = {}
    for game in games:
        if game['week'] not in weeks:
            week, created = Week.objects.get_or_create(
                season=season,
                week_number=game['week'],
                defaults={'monday_date': game['date']}
            )
            weeks[game['week']] = week
    
    # Create off weeks
    for off_week_data in off_weeks:
        OffWeek.objects.get_or_create(
            season=season,
            monday_date=off_week_data['date'],
            defaults={'title': 'Off Week', 'description': 'No games scheduled'}
        )
    
    # Assign courts based on time slots
    # Group games by week, date, and time
    from collections import defaultdict
    time_slots = defaultdict(list)
    
    for game_data in games:
        if (game_data['team1'] in season_teams and 
            game_data['team2'] in season_teams):
            key = (game_data['week'], game_data['date'], game_data['time'])
            time_slots[key].append(game_data)
    
    # Assign courts: 1 game = Court 3, 2 games = Court 2,3, 3 games = Court 1,2,3
    for time_slot_games in time_slots.values():
        num_games = len(time_slot_games)
        if num_games == 1:
            time_slot_games[0]['court'] = 'Court 3'
        elif num_games == 2:
            time_slot_games[0]['court'] = 'Court 2'
            time_slot_games[1]['court'] = 'Court 3'
        elif num_games == 3:
            time_slot_games[0]['court'] = 'Court 1'
            time_slot_games[1]['court'] = 'Court 2'
            time_slot_games[2]['court'] = 'Court 3'
        else:
            # Fallback for more than 3 games
            for i, game in enumerate(time_slot_games):
                court_num = (i % 3) + 1
                game['court'] = f'Court {court_num}'
    
    print(f"Court assignments:")
    for key, slot_games in time_slots.items():
        week, date, time = key
        print(f"  Week {week} {time}: {len(slot_games)} games - {[g['court'] for g in slot_games]}")
    
    # Create games with court assignments
    games_created = 0
    for game_data in games:
        if (game_data['team1'] in season_teams and 
            game_data['team2'] in season_teams):
            
            try:
                time_obj = datetime.strptime(game_data['time'], '%H:%M').time()
            except:
                continue
                
            # Find referee season team
            referee_season_team = None
            if game_data['referee'] in season_teams:
                referee_season_team = season_teams[game_data['referee']]
            
            game, created = Game.objects.get_or_create(
                level=levels[game_data['level']],
                week=weeks[game_data['week']],
                season_team1=season_teams[game_data['team1']],
                season_team2=season_teams[game_data['team2']],
                defaults={
                    'time': time_obj,
                    'day_of_week': 0,  # Monday
                    'team1_score': game_data['team1_score'],
                    'team2_score': game_data['team2_score'],
                    'referee_season_team': referee_season_team,
                    'court': game_data.get('court', 'Court 1'),
                }
            )
            
            if created:
                games_created += 1
    
    print(f"Import complete: {games_created} games created")
    
    # Verify game counts
    from collections import defaultdict
    team_games = defaultdict(int)
    for game in Game.objects.filter(level__season=season):
        team_games[game.get_team1_name()] += 1
        team_games[game.get_team2_name()] += 1
    
    print("\nGame counts:")
    for team, count in sorted(team_games.items()):
        status = "✓" if count == 10 else f"❌ ({count})"
        print(f"  {team}: {count} {status}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python import_schedule_simple.py <file.txt>")
        sys.exit(1)
    
    import_data(sys.argv[1])