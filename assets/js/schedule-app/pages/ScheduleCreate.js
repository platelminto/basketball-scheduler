import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, RESET_CHANGE_TRACKING, APPLY_GENERATED_SCHEDULE } from '../contexts/ScheduleContext';
import ScheduleEditor from '../components/schedule/ScheduleEditor';
import ScheduleParametersModal from '../components/ScheduleParametersModal';

const ScheduleCreate = () => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const location = useLocation();
  const [setupData, setSetupData] = useState(null);
  const [isDevelopment, setIsDevelopment] = useState(false);
  const [shouldRandomFill, setShouldRandomFill] = useState(false);
  const [showParametersModal, setShowParametersModal] = useState(false);

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
      const teamsInLevel = data.teams[levelName].map(teamData => {
        // Handle both old format (strings) and new format (objects)
        if (typeof teamData === 'string') {
          return {
            id: teamData, // In this context, we use the name as the ID
            name: teamData
          };
        } else {
          // New format: team object with id and name
          return {
            id: teamData.id,
            name: teamData.name
          };
        }
      });
      
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
            // Assign courts from highest to lowest (use last court first)
            for (let i = 0; i < timeSlot.courts; i++) {
              const gameId = `new_${Date.now()}_${Math.random()}`;

              // Create date from week start date + day offset (use UTC to avoid DST issues)
              const gameDate = new Date(week.weekStartDate);
              gameDate.setUTCDate(gameDate.getUTCDate() + parseInt(day.dayOfWeek));

              // Use courts from last to first: if 3 courts available, use Court 3, then Court 2, then Court 1
              const courtNumber = timeSlot.courts - i;

              weekData.games.push({
                id: gameId,
                day_of_week: day.dayOfWeek,
                time: timeSlot.time,
                court: `Court ${courtNumber}`,
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

  // Handle auto-generate schedule with parameters
  const autoGenerateSchedule = async (parameters, signal = null) => {
    if (!setupData) {
      throw new Error('No setup data available. Please go back to setup.');
    }

    try {
      const fetchOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          setupData: setupData,
          weekData: state.weeks,
          parameters: parameters
        })
      };
      
      // Add abort signal if provided
      if (signal) {
        fetchOptions.signal = signal;
      }
      
      const response = await fetch('/scheduler/api/seasons/0/generate/', fetchOptions);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate schedule');
      }

      const data = await response.json();
      
      // Return the data instead of automatically filling the schedule
      return data;
    } catch (error) {
      // Don't log or show alert for user cancellations
      if (error.name !== 'AbortError' && 
          !(error.name === 'DOMException' && error.message.includes('aborted'))) {
        console.error('Error generating schedule:', error);
        // Show more helpful error message with troubleshooting tips
        const errorMessage = `Error generating schedule: ${error.message}\n\n` +
          "Troubleshooting tips:\n" +
          "• Try increasing the time limit\n" +
          "• Increase max referee count or slot limits\n" +
          "• Reduce min referee count requirements\n" +
          "• Check if your court/time setup is feasible";
        
        alert(errorMessage);
      }
      
      throw error; // Re-throw so the modal can handle it
    }
  };

  // Show the parameters modal
  const showAutoGenerateModal = () => {
    setShowParametersModal(true);
  };

  // Convert raw algorithm output (with slots keys) to flat array format
  const formatRawSchedule = (rawSchedule) => {
    const formatted = [];
    let seen_off_weeks = 0;

    // Get state weeks sorted by week_number
    const sortedWeeks = Object.values(state.weeks)
      .sort((a, b) => a.week_number - b.week_number);

    for (const stateWeek of sortedWeeks) {
      if (stateWeek.isOffWeek) {
        seen_off_weeks++;
        continue;
      }

      const scheduleIdx = stateWeek.week_number - 1 - seen_off_weeks;
      if (scheduleIdx < 0 || scheduleIdx >= rawSchedule.length) {
        console.warn(`No raw schedule entry for week ${stateWeek.week_number}`);
        continue;
      }

      const scheduleWeek = rawSchedule[scheduleIdx];
      const scheduleGames = [];
      for (const slotKey of Object.keys(scheduleWeek.slots)) {
        for (const game of scheduleWeek.slots[slotKey]) {
          scheduleGames.push(game);
        }
      }

      const weekGames = [];
      stateWeek.games.forEach((game, i) => {
        if (i < scheduleGames.length) {
          const sg = scheduleGames[i];
          weekGames.push({
            id: game.id,
            level_name: sg.level,
            team1_name: sg.teams[0],
            team2_name: sg.teams[1],
            referee_name: sg.ref
          });
        }
      });

      formatted.push(weekGames);
    }

    return formatted;
  };

  // Fill schedule with auto-generated data
  const fillScheduleWithGeneratedData = (generatedSchedule, isRaw = false) => {
    try {
      // If raw format (from "Stop & Use Best"), convert to flat array first
      const schedule = isRaw ? formatRawSchedule(generatedSchedule) : generatedSchedule;

      const assignments = {};
      let lastUsedWeekNumber = 0;

      schedule.forEach((weekGames) => {
        // Find the next available non-off week
        let weekNumber = lastUsedWeekNumber + 1;
        let weekData = state.weeks[weekNumber];

        while (weekData && weekData.isOffWeek) {
          weekNumber++;
          weekData = state.weeks[weekNumber];
        }

        if (!weekData) return;
        lastUsedWeekNumber = weekNumber;

        weekGames.forEach(generatedGame => {
          const existingGame = weekData.games.find(g => g.id === generatedGame.id && !g.isDeleted);
          if (!existingGame) return;

          const assignment = {};

          // Resolve level
          if (generatedGame.level_name) {
            const levelObj = state.levels.find(l => l.name === generatedGame.level_name);
            if (levelObj) {
              assignment.level_id = levelObj.id;
              assignment.level_name = levelObj.name;
            }
          }

          const finalLevelId = assignment.level_id || existingGame.level_id;

          // Resolve teams
          if (generatedGame.team1_name && finalLevelId && state.teamsByLevel[finalLevelId]) {
            const team1Obj = state.teamsByLevel[finalLevelId].find(t => t.name === generatedGame.team1_name);
            if (team1Obj) {
              assignment.team1_id = team1Obj.id;
              assignment.team1_name = team1Obj.name;
            }
          }

          if (generatedGame.team2_name && finalLevelId && state.teamsByLevel[finalLevelId]) {
            const team2Obj = state.teamsByLevel[finalLevelId].find(t => t.name === generatedGame.team2_name);
            if (team2Obj) {
              assignment.team2_id = team2Obj.id;
              assignment.team2_name = team2Obj.name;
            }
          }

          // Resolve referee
          if (generatedGame.referee_name) {
            if (finalLevelId && state.teamsByLevel[finalLevelId]) {
              const refTeamObj = state.teamsByLevel[finalLevelId].find(t => t.name === generatedGame.referee_name);
              if (refTeamObj) {
                assignment.referee_team_id = refTeamObj.id;
                assignment.referee_name = '';
              } else {
                assignment.referee_team_id = '';
                assignment.referee_name = generatedGame.referee_name;
              }
            } else {
              assignment.referee_team_id = '';
              assignment.referee_name = generatedGame.referee_name;
            }
          }

          assignments[existingGame.id] = assignment;
        });
      });

      dispatch({
        type: APPLY_GENERATED_SCHEDULE,
        payload: { assignments }
      });
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
    const value = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
    return value || '';
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
        onAutoGenerate={showAutoGenerateModal}
      />
      
      {/* Schedule Parameters Modal */}
      <ScheduleParametersModal
        isOpen={showParametersModal}
        onClose={() => setShowParametersModal(false)}
        onGenerate={autoGenerateSchedule}
        onApply={(data) => {
          fillScheduleWithGeneratedData(data.schedule, data.isRaw || false);
        }}
        setupData={setupData}
      />
    </div>
  );
};

export default ScheduleCreate;