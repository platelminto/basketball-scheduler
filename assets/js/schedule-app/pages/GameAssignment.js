import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, TOGGLE_EDIT_MODE, RESET_CHANGE_TRACKING } from '../contexts/ScheduleContext';
import ScheduleEditor from '../components/schedule/ScheduleEditor';

const GameAssignment = () => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const location = useLocation();
  const [setupData, setSetupData] = useState(null);
  const [isDevelopment, setIsDevelopment] = useState(false);

  // Reset change tracking when component mounts to prevent stale state
  useEffect(() => {
    // Clear any leftover change tracking from previous sessions
    dispatch({ type: RESET_CHANGE_TRACKING });
  }, [dispatch]);

  // Initialize the component with the setup data from location state
  useEffect(() => {
    dispatch({ type: TOGGLE_EDIT_MODE, payload: true });
    
    // Check if we're in development mode
    const hostname = window.location.hostname;
    setIsDevelopment(hostname === 'localhost' || hostname === '127.0.0.1');

    // Get setup data from location state or URL parameter
    if (location.state && location.state.setupData) {
      const data = location.state.setupData;
      setSetupData(data);
      
      // Initialize schedule data structure
      initializeScheduleData(data);
    } else {
      // Try to get from URL parameter as fallback
      const urlParams = new URLSearchParams(window.location.search);
      const setupDataParam = urlParams.get('setupData');
      
      if (setupDataParam) {
        try {
          const data = JSON.parse(decodeURIComponent(setupDataParam));
          setSetupData(data);
          initializeScheduleData(data);
        } catch (e) {
          console.error('Error parsing setup data:', e);
          alert('Invalid setup data. Please go back and try again.');
        }
      } else {
        alert('No setup data found. Please go back and complete the team setup.');
      }
    }
  }, [location, dispatch]);

  // Initialize schedule data based on setup data
  const initializeScheduleData = (data) => {
    if (!data || !data.teams) return;
    
    const scheduleData = {
      season: {
        name: 'New Season (Unsaved)',
        id: null
      },
      weeks: {},
      levels: [],
      teamsByLevel: {},
      courts: data.courts || []
    };
    
    // Convert levels and teams
    const levels = [];
    const teamsByLevel = {};
    
    for (const levelName in data.teams) {
      const levelId = levelName; // In this context, we use the name as the ID
      
      // Add level
      levels.push({
        id: levelId,
        name: levelName
      });
      
      // Add teams for this level
      const teamsInLevel = data.teams[levelName].map(teamName => ({
        id: teamName, // In this context, we use the name as the ID
        name: teamName
      }));
      
      teamsByLevel[levelId] = teamsInLevel;
    }
    
    
    // For pre-existing schedules (from ScheduleCreate), initialize that data too
    if (data.schedule && data.schedule.weeks) {
      let weekNumber = 1;
      data.schedule.weeks.forEach(week => {
        // Skip off weeks
        if (week.isOffWeek) return;
        
        const weekData = {
          id: weekNumber,
          week_number: weekNumber,
          monday_date: week.weekStartDate, // Use week's start date directly
          games: []
        };
        
        // Process each day
        week.days.forEach(day => {
          // Process each time slot
          day.times.forEach(timeSlot => {
            // Create empty games for each court in this time slot
            for (let i = 0; i < timeSlot.courts; i++) {
              const gameId = `new_${Date.now()}_${Math.random()}`;
              
              // Create date from week start date + day offset
              const gameDate = new Date(week.weekStartDate);
              gameDate.setDate(gameDate.getDate() + parseInt(day.dayOfWeek));
              
              weekData.games.push({
                id: gameId,
                day_of_week: day.dayOfWeek,
                time: timeSlot.time,
                court: `Court ${i+1}`,
                date: gameDate.toISOString().split('T')[0], // Store the date in YYYY-MM-DD format
                level_id: '',
                level_name: '',
                team1_id: '',
                team1_name: '',
                team2_id: '',
                team2_name: '',
                team1_score: '',
                team2_score: '',
                referee_team_id: '',
                referee_name: '',
                isDeleted: false
              });
            }
          });
        });
        
        scheduleData.weeks[weekNumber] = weekData;
        weekNumber++;
      });
    }
    
    // Update state with the schedule data
    scheduleData.levels = levels;
    scheduleData.teamsByLevel = teamsByLevel;
    
    dispatch({ type: SET_SCHEDULE_DATA, payload: scheduleData });
  };

  // Handle auto-generate schedule (dev mode)
  const autoGenerateSchedule = async () => {
    if (!setupData) {
      alert('No setup data available. Please go back to setup.');
      return;
    }

    try {
      const response = await fetch('/scheduler/auto_generate_schedule/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          setupData: JSON.stringify(setupData)
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate schedule');
      }

      const data = await response.json();
      console.log('Generated schedule:', data);
      
      // TODO: Fill the form with the generated schedule
      alert('Schedule generated successfully. Display implementation pending.');
    } catch (error) {
      console.error('Error generating schedule:', error);
      alert('Error generating schedule: ' + error.message);
    }
  };

  // Handle saving the schedule
  const saveSchedule = async () => {
    if (!setupData) {
      alert('No setup data available. Please go back to setup.');
      return;
    }

    // Get a name for the season
    const seasonName = prompt("Please enter a name for this season (e.g., '24/25 Season 1'):");
    if (!seasonName || seasonName.trim() === '') {
      alert('A season name is required to save the schedule.');
      return;
    }

    // Collect game assignments and off weeks
    const gameAssignments = collectGameAssignments();
    const offWeeks = [];
    
    // Find off weeks
    for (const weekNum in state.weeks) {
      const weekData = state.weeks[weekNum];
      if (weekData.isOffWeek) {
        offWeeks.push({
          week_number: weekData.week_number,
          monday_date: weekData.monday_date
        });
      }
    }
    
    if (gameAssignments.length === 0 && offWeeks.length === 0) {
      alert('No games or off weeks to save. Please create some weeks first.');
      return;
    }

    // Create the payload
    const payload = {
      season_name: seasonName.trim(),
      setupData: JSON.stringify(setupData),
      game_assignments: gameAssignments,
      off_weeks: offWeeks
    };

    try {
      const response = await fetch('/scheduler/save_schedule/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Schedule saved successfully. Created ${data.games_created} games in season "${seasonName}".`);
        navigate('/');
      } else {
        alert(`Error: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Network error: ${error.message}`);
      console.error('Error:', error);
    }
  };

  // Collect all game assignments from the state
  const collectGameAssignments = () => {
    const gameAssignments = [];
    const offWeeks = [];
    
    // Check if there are weeks in the state
    if (!state.weeks || Object.keys(state.weeks).length === 0) {
      return gameAssignments;
    }

    // Iterate through all weeks
    for (const weekNum in state.weeks) {
      const weekData = state.weeks[weekNum];
      
      // Check if this is an off week
      if (weekData.isOffWeek) {
        offWeeks.push({
          week: weekData.week_number,
          monday_date: weekData.monday_date
        });
        continue; // Skip to the next week
      }
      
      // Iterate through all games in this week
      weekData.games.forEach(game => {
        // Skip games that are marked for deletion
        if (game.isDeleted) {
          return;
        }

        // Get referee value (either team ID or name)
        let referee = game.referee_team_id || "";
        if (!referee && game.referee_name) {
          referee = game.referee_name;
        }

        gameAssignments.push({
          week: weekData.week_number,
          dayOfWeek: game.day_of_week,
          time: game.time,
          gameIndex: 0, // Will be determined based on time sorting
          level: game.level_id,
          team1: game.team1_id,
          team2: game.team2_id,
          referee: referee,
          court: game.court
        });
      });
    }
    
    // Add off_weeks property to the first item in gameAssignments to pass it along
    if (gameAssignments.length > 0 && offWeeks.length > 0) {
      gameAssignments[0].off_weeks = offWeeks;
    }
    
    return gameAssignments;
  };

  // Get CSRF token for form submissions
  const getCsrfToken = () => {
    return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  };

  // If setup data is not available, show a message
  if (!setupData) {
    return (
      <div className="container mt-4">
        <div className="alert alert-warning">
          <h4><i className="fas fa-exclamation-triangle"></i> Setup Data Missing</h4>
          <p>No setup data found. Please go back and complete the team setup step.</p>
          <button 
            className="btn btn-primary" 
            onClick={() => navigate(-1)}
          >
            Back to Team Setup
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container-fluid mt-4">
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <div>
          <h2>Step 2: Schedule Creation & Game Assignment</h2>
          <p className="text-muted">Create your schedule and assign teams to games.</p>
        </div>

        {/* Dev mode buttons */}
        {isDevelopment && (
          <div className="d-flex gap-2">
            <button 
              type="button" 
              className="btn btn-info" 
              onClick={autoGenerateSchedule}
            >
              Auto-generate Schedule
            </button>
          </div>
        )}
      </div>

      {/* Back to Team Setup button */}
      <div className="mb-3">
        <button 
          type="button" 
          className="btn btn-secondary" 
          onClick={() => navigate(-1)}
        >
          Back to Team Setup
        </button>
      </div>

      {/* Schedule Editor Component */}
      <ScheduleEditor 
        mode="create"
        showValidation={true}
        onSave={saveSchedule}
      />
    </div>
  );
};

export default GameAssignment;