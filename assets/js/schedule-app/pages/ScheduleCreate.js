import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, RESET_CHANGE_TRACKING, UPDATE_GAME } from '../contexts/ScheduleContext';
import ScheduleEditor from '../components/schedule/ScheduleEditor';

const ScheduleCreate = () => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const location = useLocation();
  const [setupData, setSetupData] = useState(null);
  const [isDevelopment, setIsDevelopment] = useState(false);
  const [shouldRandomFill, setShouldRandomFill] = useState(false);

  // Reset change tracking when component mounts to prevent stale state
  useEffect(() => {
    // Clear any leftover change tracking from previous sessions
    dispatch({ type: RESET_CHANGE_TRACKING });
  }, [dispatch]);

  // Initialize the component with the setup data from location state
  useEffect(() => {
    // No need to toggle editing mode - ScheduleEditor uses mode prop
    
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
      const response = await fetch('/scheduler/api/seasons/0/generate/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          setupData: setupData,
          weekData: state.weeks,
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate schedule');
      }

      const data = await response.json();
      console.log('Generated schedule:', data);
      
      // Fill the form with the generated schedule
      fillScheduleWithGeneratedData(data.schedule);
    } catch (error) {
      console.error('Error generating schedule:', error);
      alert('Error generating schedule: ' + error.message);
    }
  };

  // Fill schedule with auto-generated data
  const fillScheduleWithGeneratedData = (generatedSchedule) => {
    try {
      let lastUsedWeekNumber = 0; // Track the last week we used
      
      // Process each week in the generated schedule
      generatedSchedule.forEach((weekGames, weekIndex) => {
        // Find the next available non-off week starting from where we left off
        let weekNumber = lastUsedWeekNumber + 1;
        let weekData = state.weeks[weekNumber];
        
        // Keep incrementing until we find a non-off week
        while (weekData && weekData.isOffWeek) {
          weekNumber++;
          weekData = state.weeks[weekNumber];
        }
        
        if (!weekData) {
          console.warn(`No more weeks available for generated schedule entry ${weekIndex}`);
          return;
        }
        
        // Update our tracking variable
        lastUsedWeekNumber = weekNumber;
        
        // Create a map of existing games by their ID for quick lookup
        const existingGamesMap = {};
        weekData.games.forEach((game, gameIndex) => {
          if (!game.isDeleted) {
            existingGamesMap[game.id] = { game, index: gameIndex };
          }
        });
        
        // Process each generated game
        weekGames.forEach(generatedGame => {
          // Find the corresponding existing game by ID
          const gameInfo = existingGamesMap[generatedGame.id];
          
          if (gameInfo) {
            const existingGame = gameInfo.game;
            let levelId = null;
            
            // First, handle level assignment and get the levelId for team lookups
            if (generatedGame.level_name) {
              const levelObj = state.levels.find(l => l.name === generatedGame.level_name);
              if (levelObj) {
                levelId = levelObj.id;
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'level_id', value: levelObj.id }
                });
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'level_name', value: levelObj.name }
                });
              }
            }
            
            // Use the levelId we just determined or fall back to existing level_id
            const finalLevelId = levelId || existingGame.level_id;
            
            // Update team1 data
            if (generatedGame.team1_name && finalLevelId && state.teamsByLevel[finalLevelId]) {
              const team1Obj = state.teamsByLevel[finalLevelId].find(t => t.name === generatedGame.team1_name);
              if (team1Obj) {
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'team1_id', value: team1Obj.id }
                });
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'team1_name', value: team1Obj.name }
                });
              }
            }
            
            // Update team2 data
            if (generatedGame.team2_name && finalLevelId && state.teamsByLevel[finalLevelId]) {
              const team2Obj = state.teamsByLevel[finalLevelId].find(t => t.name === generatedGame.team2_name);
              if (team2Obj) {
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'team2_id', value: team2Obj.id }
                });
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'team2_name', value: team2Obj.name }
                });
              }
            }
            
            // Update referee data
            if (generatedGame.referee_name) {
              if (finalLevelId && state.teamsByLevel[finalLevelId]) {
                const refTeamObj = state.teamsByLevel[finalLevelId].find(t => t.name === generatedGame.referee_name);
                if (refTeamObj) {
                  dispatch({
                    type: UPDATE_GAME,
                    payload: { gameId: existingGame.id, field: 'referee_team_id', value: refTeamObj.id }
                  });
                  dispatch({
                    type: UPDATE_GAME,
                    payload: { gameId: existingGame.id, field: 'referee_name', value: '' }
                  });
                } else {
                  // If not found as a team, treat as a name
                  dispatch({
                    type: UPDATE_GAME,
                    payload: { gameId: existingGame.id, field: 'referee_team_id', value: '' }
                  });
                  dispatch({
                    type: UPDATE_GAME,
                    payload: { gameId: existingGame.id, field: 'referee_name', value: generatedGame.referee_name }
                  });
                }
              } else {
                // If no level or teamsByLevel, treat as a name
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'referee_team_id', value: '' }
                });
                dispatch({
                  type: UPDATE_GAME,
                  payload: { gameId: existingGame.id, field: 'referee_name', value: generatedGame.referee_name }
                });
              }
            }
          } else {
            console.warn(`Game with ID ${generatedGame.id} not found in week ${weekNumber}`);
          }
        });
      });
      
      alert('Schedule generated and filled successfully!');
    } catch (error) {
      console.error('Error filling schedule with generated data:', error);
      alert('Error filling schedule: ' + error.message);
    }
  };

  // Handle saving the schedule
  const saveSchedule = async (scheduleData) => {
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

    const { gameAssignments, weekDates, offWeeks } = scheduleData;
    
    if (gameAssignments.length === 0 && offWeeks.length === 0) {
      alert('No games or off weeks to save. Please create some weeks first.');
      return;
    }

    // Create the payload
    const payload = {
      season_name: seasonName.trim(),
      setupData: setupData,
      game_assignments: gameAssignments,
      week_dates: weekDates,
      off_weeks: offWeeks,
      skip_validation: true
    };

    try {
      const response = await fetch('/scheduler/api/seasons/', {
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
        alert(`Error: ${data.message || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Network error: ${error.message}`);
      console.error('Error:', error);
    }
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

        {/* Action buttons */}
        <div className="d-flex gap-2">
          {/* Random Fill button */}
          <button 
            type="button" 
            className="btn btn-warning" 
            onClick={() => setShouldRandomFill(true)}
          >
            Random Fill
          </button>
        </div>
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
        shouldRandomFill={shouldRandomFill}
        onRandomFillComplete={() => setShouldRandomFill(false)}
        isDevelopment={isDevelopment}
        onAutoGenerate={autoGenerateSchedule}
      />
    </div>
  );
};

export default ScheduleCreate;