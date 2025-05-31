import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, TOGGLE_EDIT_MODE, SET_LOADING, SET_ERROR, RESET_CHANGE_TRACKING } from '../contexts/ScheduleContext';
import ScheduleEditor from '../components/schedule/ScheduleEditor';
import ValidationResults from '../components/schedule/ValidationResults';

const ScheduleEdit = () => {
  // Get seasonId from Router params
  const { seasonId } = useParams();
  const navigate = useNavigate();
  const { state, dispatch } = useSchedule();
  const [isEditingEnabled, setIsEditingEnabled] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [validationPassed, setValidationPassed] = useState(false);
  const [validationResults, setValidationResults] = useState(null);
  const [ignoredFailures, setIgnoredFailures] = useState(new Set());


  // Reset change tracking when component mounts to prevent stale state
  useEffect(() => {
    // Clear any leftover change tracking from previous sessions
    dispatch({ type: RESET_CHANGE_TRACKING });
    
    // Also reset any validation state
    setValidationResults(null);
    setIgnoredFailures(new Set());
    setValidationPassed(false);
  }, [dispatch]);

  // Clear validation results when schedule changes
  useEffect(() => {
    if (validationResults) {
      console.log('Clearing validation due to schedule changes');
      
      // Clear local state
      setValidationResults(null);
      setIgnoredFailures(new Set());
      setValidationPassed(false);
    }
  }, [state.changedGames, state.newGames, state.changedWeeks]);

  useEffect(() => {
    // Fetch schedule data when component mounts
    const fetchScheduleData = async () => {
      dispatch({ type: SET_LOADING, payload: true });

      try {
        console.log(`Fetching data from: /scheduler/api/schedule/${seasonId}/`);
        const response = await fetch(`/scheduler/api/schedule/${seasonId}/`);

        if (!response.ok) {
          console.error(`API Error: ${response.status} ${response.statusText}, URL: /scheduler/api/schedule/${seasonId}/`);
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Successfully fetched schedule data');
        dispatch({ type: SET_SCHEDULE_DATA, payload: data });
      } catch (error) {
        console.error('Error fetching schedule data:', error);
        dispatch({ type: SET_ERROR, payload: 'Failed to load schedule data. Please try again.' });
      }
    };

    if (seasonId) {
      fetchScheduleData();
    }
  }, [seasonId, dispatch]);


  const handleEditToggle = (enabled) => {
    // Don't allow enabling schedule editing if there are unsaved score changes
    if (enabled && state.changedGames.size > 0) {
      alert("Please save your score changes before enabling schedule editing.");
      return;
    }
    
    // If turning off editing with schedule changes, ask for confirmation
    if (!enabled && (state.changedGames.size > 0 || state.newGames.size > 0 || 
        Object.values(state.weeks).some(week => week.games && week.games.some(game => game.isDeleted)) ||
        state.changedWeeks.size > 0)) {
      
      const confirmDisable = window.confirm(
        "Turning off schedule editing will discard any unsaved schedule changes. Are you sure you want to continue?"
      );
      
      if (!confirmDisable) {
        return; // Don't disable editing if user cancels
      }
      
      // User confirmed - reload the page to discard all changes
      window.location.reload();
      return;
    }
    
    setIsEditingEnabled(enabled);
    
    // Reset validation status when toggling edit mode
    setValidationPassed(false);
    
    dispatch({ type: TOGGLE_EDIT_MODE, payload: enabled });
  };
  
  // Simple validation function that calls the backend
  const validateSchedule = async () => {
    setIsValidating(true);
    
    try {
      // Collect data using the same approach as ScheduleEditor
      const gameAssignments = collectGameAssignments();
      
      // Convert to backend format for validation
      const scheduleData = webToScheduleFormat(gameAssignments);
      
      // Extract config from game assignments - Use names like ScheduleEditor does
      const levels = [];
      const teams_per_level = {};
      
      for (let levelId of Object.keys(state.teamsByLevel)) {
        levelId = parseInt(levelId);
        if (state.teamsByLevel[levelId].length > 0) {
          const level = state.levels.find(l => l.id === levelId);
          if (level) {
            levels.push(level.name); // Use level name instead of ID
            teams_per_level[level.name] = state.teamsByLevel[levelId].length; // Use level name as key
          }
        }
      }
      
      const minimalConfig = { levels, teams_per_level };
      
      // Call validation API
      const response = await fetch('/scheduler/validate_schedule/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          schedule: scheduleData,
          config: minimalConfig
        })
      });
      
      const data = await response.json();
      setValidationResults(data);
      
      // Check if all validation tests passed or are ignored
      checkValidationState(data);
    } catch (error) {
      console.error('Error validating schedule:', error);
      alert('Error during validation: ' + error.message);
    } finally {
      setIsValidating(false);
    }
  };
  
  const checkValidationState = (results = validationResults) => {
    if (!results) return;

    let allPassedOrIgnored = true;
    
    for (const testName in results) {
      if (!results[testName].passed && !ignoredFailures.has(testName)) {
        allPassedOrIgnored = false;
        break;
      }
    }

    setValidationPassed(allPassedOrIgnored);
  };
  
  const handleIgnoreFailure = (testName, isIgnored) => {
    const updatedIgnores = new Set(ignoredFailures);
    
    if (isIgnored) {
      updatedIgnores.add(testName);
    } else {
      updatedIgnores.delete(testName);
    }
    
    setIgnoredFailures(updatedIgnores);
    
    // Directly calculate the new validation state
    let allPassedOrIgnored = true;
    
    for (const name in validationResults) {
      if (!validationResults[name].passed && !updatedIgnores.has(name)) {
        allPassedOrIgnored = false;
        break;
      }
    }
    
    setValidationPassed(allPassedOrIgnored);
  };

  // Helper functions for validation - same as ScheduleEditor
  const collectGameAssignments = () => {
    const gameAssignments = [];
    
    if (!state.weeks || Object.keys(state.weeks).length === 0) {
      return gameAssignments;
    }
    
    for (const weekNum in state.weeks) {
      const weekData = state.weeks[weekNum];
      
      weekData.games.forEach(game => {
        if (game.isDeleted) {
          return;
        }
        
        let referee = game.referee_team_id || "";
        if (!referee && game.referee_name) {
          referee = game.referee_name;
        }
        
        gameAssignments.push({
          week: weekData.week_number,
          dayOfWeek: game.day_of_week,
          time: game.time,
          gameIndex: 0,
          level: game.level_id,
          team1: game.team1_id,
          team2: game.team2_id,
          referee: referee,
          court: game.court
        });
      });
    }
    
    return gameAssignments;
  };
  
  const webToScheduleFormat = (gameAssignments) => {
    // Same logic as ScheduleEditor
    const weekGroups = {};
    gameAssignments.forEach(game => {
      const weekKey = game.week;
      
      if (!weekGroups[weekKey]) {
        weekGroups[weekKey] = {
          week: weekKey,
          slots: {}
        };
      }
      
      const timeStr = game.time;
      let slotNum = 1;
      const slots = weekGroups[weekKey].slots;
      
      let foundSlot = false;
      for (const slotKey in slots) {
        const gamesInSlot = slots[slotKey];
        if (gamesInSlot.length > 0 && gamesInSlot[0].time === timeStr) {
          slotNum = parseInt(slotKey);
          foundSlot = true;
          break;
        }
      }
      
      if (!foundSlot) {
        slotNum = Object.keys(slots).length + 1;
      }
      
      if (!slots[slotNum]) {
        slots[slotNum] = [];
      }
      
      // Convert IDs to names for validation
      const level = state.levels.find(l => l.id === game.level);
      const levelName = level ? level.name : game.level;
      
      // Find team names
      let team1Name = game.team1;
      let team2Name = game.team2;
      let refName = game.referee;
      
      if (level && state.teamsByLevel[level.id]) {
        const team1Obj = state.teamsByLevel[level.id].find(t => t.id === game.team1);
        const team2Obj = state.teamsByLevel[level.id].find(t => t.id === game.team2);
        
        team1Name = team1Obj ? team1Obj.name : game.team1;
        team2Name = team2Obj ? team2Obj.name : game.team2;
        
        // Handle referee - could be team ID or a name
        if (game.referee) {
          const refObj = state.teamsByLevel[level.id].find(t => t.id === game.referee);
          refName = refObj ? refObj.name : game.referee;
        }
      }
      
      slots[slotNum].push({
        level: levelName,
        teams: [team1Name, team2Name],
        ref: refName || "External Ref",
        time: timeStr
      });
    });
    
    return Object.values(weekGroups);
  };

  const handleSaveChanges = async (scheduleData = null) => {
    // If nothing has changed, show alert and return
    // Check if any games are marked as deleted
    const hasDeletedGames = Object.values(state.weeks).some(week =>
      week.games.some(game => game.isDeleted)
    );

    if (
      state.changedGames.size === 0 &&
      state.newGames.size === 0 &&
      !hasDeletedGames &&
      state.changedWeeks.size === 0
    ) {
      alert('No changes detected. Form not submitted.');
      return;
    }
    
    // For schedule changes, validate before saving if not already validated
    if (isEditingEnabled && !validationPassed) {
      alert('Please validate the schedule before saving.');
      return;
    }

    // Validate all games first
    const invalidGames = [];

    // Check all games for validity
    for (const weekNum in state.weeks) {
      const weekData = state.weeks[weekNum];

      weekData.games.forEach(game => {
        // Skip games that are marked for deletion
        if (game.isDeleted) {
          return;
        }

        // Validate required fields - be more lenient with types
        const hasLevel = Boolean(game.level_id);
        const hasTeam1 = Boolean(game.team1_id);
        const hasTeam2 = Boolean(game.team2_id);
        const hasDay = game.day_of_week !== undefined && game.day_of_week !== null && game.day_of_week !== '';
        const hasTime = Boolean(game.time);

        if (!hasLevel || !hasTeam1 || !hasTeam2 || !hasDay || !hasTime) {
          invalidGames.push({
            week: weekData.week_number,
            game: game
          });
        }
      });
    }

    // If any games are invalid, stop and show an error
    if (invalidGames.length > 0) {
      const errorMsg = `Cannot save: ${invalidGames.length} game(s) have missing required fields.\n\n` +
                      invalidGames.map(ig => {
                        const game = ig.game;
                        const missingFields = [];

                        if (!game.level_id) missingFields.push('Level');
                        if (!game.team1_id) missingFields.push('Team 1');
                        if (!game.team2_id) missingFields.push('Team 2');
                        if (game.day_of_week === undefined || game.day_of_week === null || game.day_of_week === '')
                          missingFields.push('Day');
                        if (!game.time) missingFields.push('Time');

                        return `Week ${ig.week}: ${game.team1_name || 'Unknown'} vs ${game.team2_name || 'Unknown'} - Missing: ${missingFields.join(', ')}`;
                      }).join('\n');
      alert(errorMsg);
      console.error('Invalid games:', invalidGames);
      return;
    }

    let games, weekDateChanges, offWeeks;

    if (scheduleData) {
      // Use data from ScheduleEditor
      const { gameAssignments, weekDates, offWeeks: scheduleOffWeeks } = scheduleData;
      
      games = gameAssignments.map(assignment => ({
        id: null, // New games from schedule editor
        week: assignment.week,
        day: assignment.dayOfWeek,
        time: assignment.time,
        court: assignment.court,
        level: assignment.level,
        team1: assignment.team1,
        team2: assignment.team2,
        score1: '',
        score2: '',
        referee: assignment.referee
      }));

      weekDateChanges = weekDates.map(week => ({
        id: week.week_number, // Use week number as ID for new weeks
        date: week.monday_date,
        isOffWeek: week.is_off_week
      }));

      offWeeks = scheduleOffWeeks.map(week => ({
        week_id: week.week_number,
        week_number: week.week_number,
        date: week.monday_date
      }));
    } else {
      // Legacy path for direct button clicks
      games = [];

      // Include ALL games from all weeks (not marked for deletion)
      for (const weekNum in state.weeks) {
        const weekData = state.weeks[weekNum];

        weekData.games.forEach(game => {
          // Skip games that are marked for deletion
          if (game.isDeleted) {
            return;
          }

          // For new games, use null ID
          const gameId = state.newGames.has(game.id) ? null : game.id;

          games.push({
            id: gameId,
            week: weekData.week_number,
            day: game.day_of_week,
            time: game.time,
            court: game.court,
            level: game.level_id,
            team1: game.team1_id,
            team2: game.team2_id,
            score1: game.team1_score !== null && game.team1_score !== undefined ? String(game.team1_score) : '',
            score2: game.team2_score !== null && game.team2_score !== undefined ? String(game.team2_score) : '',
            referee: game.referee_team_id ? game.referee_team_id :
                    game.referee_name ? 'name:' + game.referee_name : ''
          });
        });
      }

      // For editing mode, collect all week dates, not just changed ones
      weekDateChanges = [];
      offWeeks = [];
      
      if (isEditingEnabled) {
        // When in editing mode, send all week dates to ensure backend has complete week information
        for (const weekNum in state.weeks) {
          const weekData = state.weeks[weekNum];
          
          weekDateChanges.push({
            id: weekData.week_number, // Use week number as ID for consistency
            date: weekData.monday_date,
            isOffWeek: !!weekData.isOffWeek
          });
          
          if (weekData.isOffWeek) {
            offWeeks.push({
              week_id: weekData.week_number,
              week_number: weekData.week_number,
              date: weekData.monday_date
            });
          }
        }
      } else {
        // For score-only changes, only send changed weeks
        Array.from(state.changedWeeks).forEach(weekId => {
          const weekData = state.weeks[weekId];

          if (weekData) {
            weekDateChanges.push({
              id: weekData.id,
              date: weekData.monday_date,
              isOffWeek: !!weekData.isOffWeek
            });
            
            // Track off weeks separately
            if (weekData.isOffWeek) {
              offWeeks.push({
                week_id: weekData.id,
                week_number: weekData.week_number,
                date: weekData.monday_date
              });
            }
          }
        });
      }
    }

    try {
      // Log the data being sent
      console.log('Sending data to server:', {
        games,
        week_dates: weekDateChanges,
        off_weeks: offWeeks
      });

      const response = await fetch(`/scheduler/save_or_update_schedule/${seasonId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          games: games,
          week_dates: weekDateChanges,
          off_weeks: offWeeks
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert(data.message);
        window.location.reload();
      } else {
        alert(`Error: ${data.message || 'Unknown error'}`);
        console.error('Error details:', data.error);
      }
    } catch (error) {
      alert(`Network error: ${error.message}`);
      console.error('Error:', error);
    }
  };

  if (state.isLoading) {
    return <div className="container mt-5">Loading schedule data...</div>;
  }

  if (state.error) {
    return (
      <div className="container mt-4">
        <div className="alert alert-danger" role="alert">
          {state.error}
          <button
            className="btn btn-outline-primary ms-3"
            onClick={() => window.location.reload()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Get CSRF token for form submissions
  const getCsrfToken = () => {
    return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  };

  return (
    <div className="container-fluid mt-4">
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <h2>Edit Schedule/Scores: {state.season?.name}</h2>

        <div className="form-check form-switch align-self-center"
             title={!isEditingEnabled && state.changedGames.size > 0 ? "Save your score changes before enabling schedule editing" : ""}>
          <input
            className="form-check-input"
            type="checkbox"
            role="switch"
            id="enableScheduleEditToggle"
            checked={isEditingEnabled}
            onChange={(e) => handleEditToggle(e.target.checked)}
            disabled={!isEditingEnabled && state.changedGames.size > 0}
          />
          <label className="form-check-label" htmlFor="enableScheduleEditToggle">
            Enable Schedule Editing
          </label>
        </div>

        <div className="d-flex gap-2">
          <Link to="/" className="btn btn-secondary">
            Back to Seasons List
          </Link>
          
          {/* Button logic based on editing state and validation */}
          {isEditingEnabled ? (
            <>
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={() => {
                  if (window.confirm('Are you sure you want to reset all changes? This will reload the page and discard any unsaved changes.')) {
                    window.location.reload();
                  }
                }}
              >
                Reset Changes
              </button>
              
              {/* When schedule editing is enabled, show Validate or Save button based on validation status */}
              <button
                type="button"
                className={validationPassed ? "btn btn-success" : "btn btn-primary"}
                onClick={validationPassed ? () => handleSaveChanges(null) : validateSchedule}
                disabled={isValidating}
              >
                {isValidating ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Validating...
                  </>
                ) : (
                  validationPassed ? 'Save Schedule Changes' : 'Validate Schedule'
                )}
              </button>
            </>
          ) : (
            // When only score editing is enabled, just show Save Score Changes button
            <button
              type="button"
              className="btn btn-success"
              onClick={() => handleSaveChanges(null)}
            >
              Save Score Changes
            </button>
          )}
        </div>
      </div>

      {/* Show validation results when available */}
      {validationResults && (
        <div className="mb-4">
          <ValidationResults
            validationResults={validationResults}
            ignoredFailures={ignoredFailures}
            onIgnoreFailure={handleIgnoreFailure}
            allPassedOrIgnored={validationPassed}
            onValidationChange={(passed) => setValidationPassed(passed)}
          />
        </div>
      )}

      {/* Schedule Editor Component */}
      <ScheduleEditor 
        mode="edit"
        showValidation={false}
        onSave={(scheduleData) => handleSaveChanges(scheduleData)}
        seasonId={seasonId}
      />
    </div>
  );
};

export default ScheduleEdit;