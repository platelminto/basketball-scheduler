from django.test import TestCase, Client
from django.urls import reverse
from scheduler.models import Season, Level, Team, Game, Week
from datetime import date, time
from icalendar import Calendar


class TeamCalendarExportTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test season, level, and teams
        self.season = Season.objects.create(
            name='Test Season', 
            is_active=True, 
            slot_duration_minutes=70
        )
        self.level = Level.objects.create(season=self.season, name='Test Level')
        self.team1 = Team.objects.create(level=self.level, name='Team A')
        self.team2 = Team.objects.create(level=self.level, name='Team B')
        self.team3 = Team.objects.create(level=self.level, name='Team C')
        
        # Create test week
        self.week = Week.objects.create(
            season=self.season, 
            week_number=1, 
            monday_date=date(2025, 1, 6)
        )
        
        # Create test games (day_of_week: 0=Monday, 1=Tuesday, etc.)
        self.game1 = Game.objects.create(
            level=self.level,
            week=self.week,
            team1=self.team1,
            team2=self.team2,
            referee_team=self.team3,
            day_of_week=0,  # Monday
            time=time(19, 0),
            court='Court 1'
        )
        
        self.game2 = Game.objects.create(
            level=self.level,
            week=self.week,
            team1=self.team2,
            team2=self.team3,
            referee_team=self.team1,
            day_of_week=2,  # Wednesday
            time=time(20, 0),
            court='Court 2'
        )

    def test_calendar_export_basic(self):
        """Test basic calendar export functionality"""
        url = reverse('scheduler:team_calendar_export', args=[self.team1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/calendar; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Team A-schedule.ics', response['Content-Disposition'])
        
        # Parse the calendar content
        cal = Calendar.from_ical(response.content)
        events = [component for component in cal.walk() if component.name == "VEVENT"]
        
        # Should have 1 playing game (team1 vs team2) by default
        self.assertEqual(len(events), 1)
        
        event = events[0]
        self.assertIn('vs Team B', str(event.get('summary')))
        self.assertEqual(str(event.get('location')), 'Court 1')

    def test_calendar_export_with_reffing(self):
        """Test calendar export including reffing games"""
        url = reverse('scheduler:team_calendar_export', args=[self.team1.id])
        response = self.client.get(url + '?include_reffing=true')
        
        self.assertEqual(response.status_code, 200)
        
        # Parse the calendar content
        cal = Calendar.from_ical(response.content)
        events = [component for component in cal.walk() if component.name == "VEVENT"]
        
        # Should have 2 games: 1 playing + 1 reffing
        self.assertEqual(len(events), 2)
        
        summaries = [str(event.get('summary')) for event in events]
        self.assertIn('Team A vs Team B', summaries)  # Playing game
        self.assertIn('Ref: Team B vs Team C', summaries)  # Reffing game

    def test_calendar_export_with_scores(self):
        """Test calendar export including final scores"""
        # Add scores to completed game
        self.game1.team1_score = 85
        self.game1.team2_score = 78
        self.game1.save()
        
        url = reverse('scheduler:team_calendar_export', args=[self.team1.id])
        response = self.client.get(url + '?include_scores=true')
        
        self.assertEqual(response.status_code, 200)
        
        # Parse the calendar content
        cal = Calendar.from_ical(response.content)
        events = [component for component in cal.walk() if component.name == "VEVENT"]
        
        self.assertEqual(len(events), 1)
        
        event = events[0]
        description = str(event.get('description'))
        self.assertIn('Final Score: Team A 85 - 78 Team B', description)

    def test_calendar_export_nonexistent_team(self):
        """Test calendar export for nonexistent team returns 404"""
        url = reverse('scheduler:team_calendar_export', args=[99999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_calendar_properties(self):
        """Test that calendar has proper properties"""
        url = reverse('scheduler:team_calendar_export', args=[self.team1.id])
        response = self.client.get(url)
        
        cal = Calendar.from_ical(response.content)
        
        self.assertEqual(str(cal.get('version')), '2.0')
        self.assertEqual(str(cal.get('calscale')), 'GREGORIAN')
        self.assertIn('Team A', str(cal.get('x-wr-calname')))
        self.assertIn('Test Season', str(cal.get('x-wr-calname')))


if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'basketball_scheduler.settings')
    django.setup()
    
    import unittest
    unittest.main()