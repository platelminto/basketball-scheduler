import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, SET_LOADING, SET_ERROR, RESET_CHANGE_TRACKING } from '../contexts/ScheduleContext';
import ScheduleEditor from '../components/schedule/ScheduleEditor';
import ValidationResults from '../components/schedule/ValidationResults';
import { webToScheduleFormat } from '../utils/scheduleDataTransforms';

const ScheduleEdit = () => {
  // Get seasonId from Router params
  const { seasonId } = useParams();
  const { state, dispatch } = useSchedule();
  // Schedule editing is always enabled in this component
  const [isValidating, setIsValidating] = useState(false);
  const [validationPassed, setValidationPassed] = useState(false);
  const [validationResults, setValidationResults] = useState(null);
  const [ignoredFailures, setIgnoredFailures] = useState(new Set());
  // Schedule editing uses table view by default
  const [useSimpleView, setUseSimpleView] = useState(false);
  const hasScrolledRef = useRef(false);


  // Reset change tracking when component mounts to prevent stale state
  useEffect(() => {
    // Clear any leftover change tracking from previous sessions
    dispatch({ type: RESET_CHANGE_TRACKING });
    
    // Also reset any validation state
    setValidationResults(null);
    setIgnoredFailures(new Set());
    setValidationPassed(false);
    
    // Reset scroll tracking
    hasScrolledRef.current = false;
  }, [dispatch]);

  // Clear validation results when schedule changes
  useEffect(() => {
    // Only clear if we have validation results
    if (validationResults &&
        (state.changedGames.size > 0 || 
         state.newGames.size > 0 || 
         state.changedWeeks.size > 0 ||
         Object.values(state.weeks).some(week => week.games && week.games.some(game => game.isDeleted)))) {
      
      console.log('Clearing validation due to schedule changes');
      
      // Clear local state
      setValidationResults(null);
      setIgnoredFailures(new Set());
      setValidationPassed(false);
    }
  }, [state.changedGames, state.newGames, state.changedWeeks, state.weeks]);

  // Scroll to validation results when they appear
  useEffect(() => {
    if (validationResults) {
      // Add a small delay to ensure the validation results are fully rendered
      setTimeout(() => {
        const validationElement = document.querySelector('.validation-results');
        if (validationElement) {
          validationElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start',
            inline: 'nearest' 
          });
        }
      }, 100);
    }
  }, [validationResults]);

  useEffect(() => {
    // Fetch schedule data when component mounts
    const fetchScheduleData = async () => {
      dispatch({ type: SET_LOADING, payload: true });

      try {
        console.log(`Fetching data from: /scheduler/api/seasons/${seasonId}/`);
        const response = await fetch(`/scheduler/api/seasons/${seasonId}/`);

        if (!response.ok) {
          console.error(`API Error: ${response.status} ${response.statusText}, URL: /scheduler/api/seasons/${seasonId}/`);
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Successfully fetched schedule data:', data);
        console.log('Weeks in data:', data.weeks);
        // Check specifically for off weeks
        Object.entries(data.weeks || {}).forEach(([weekId, week]) => {
          if (week.isOffWeek) {
            console.log('Found off week in API response:', weekId, week);
          }
        });
        dispatch({ type: SET_SCHEDULE_DATA, payload: { ...data, disableLocks: true } });
      } catch (error) {
        console.error('Error fetching schedule data:', error);
        dispatch({ type: SET_ERROR, payload: 'Failed to load schedule data. Please try again.' });
      }
    };

    if (seasonId) {
      fetchScheduleData();
    }
  }, [seasonId, dispatch]);

  // No auto-scroll for schedule editing page - let users navigate manually


  // No toggle needed - components use mode prop instead of global editing state
  
  // Simple validation function that calls the backend
  const validateSchedule = async () => {
    setIsValidating(true);
    
    try {
      // Collect data using the same approach as ScheduleEditor
      const gameAssignments = collectGameAssignments();
      
      // Convert to backend format for validation
      const scheduleData = webToScheduleFormat(gameAssignments, state);
      
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
      
      // Debug logging
      console.log('Validation - Game Assignments:', gameAssignments.length);
      console.log('Validation - Schedule Data:', scheduleData);
      console.log('Validation - Config:', minimalConfig);
      
      // Call validation API
      const response = await fetch('/scheduler/api/seasons/validate/', {
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
        
        let referee = game.referee_team_id ? String(game.referee_team_id) : "";
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
    if (!validationPassed) {
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
            referee: game.referee_team_id ? String(game.referee_team_id) :
                    game.referee_name ? 'name:' + game.referee_name : ''
          });
        });
      }

      // For schedule editing mode, send all week dates to ensure backend has complete week information
      weekDateChanges = [];
      offWeeks = [];
      
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
    }

    try {
      // Log the data being sent
      console.log('Sending data to server:', {
        games,
        week_dates: weekDateChanges,
        off_weeks: offWeeks
      });

      const response = await fetch(`/scheduler/api/seasons/${seasonId}/schedule/`, {
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
        <h2>Edit Schedule Structure: {state.season?.name}</h2>

        <div className="d-flex gap-3 align-items-center">
        </div>

        <div className="d-flex gap-2 mb-3">
          <Link to="/" className="btn btn-secondary">
            Back to Seasons List
          </Link>
          
          {/* Reset Changes button - always available */}
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
          
          {/* Schedule editing validation and save */}
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
        </div>
      </div>

      {/* Show validation results when available */}
      {validationResults && (
        <div className="mb-4 validation-results">
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
        mode="schedule-edit"
        showValidation={false}
        onSave={(scheduleData) => handleSaveChanges(scheduleData)}
        seasonId={seasonId}
        useSimpleView={useSimpleView}
      />
    </div>
  );
};

export default ScheduleEdit;