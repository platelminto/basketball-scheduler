import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { useScheduleValidation } from '../hooks/useScheduleValidation';
import { SET_SCHEDULE_DATA, SET_LOADING, SET_ERROR, RESET_CHANGE_TRACKING } from '../contexts/ScheduleContext';
import ScheduleEditor from '../components/schedule/ScheduleEditor';
import ValidationResults from '../components/schedule/ValidationResults';

const ScheduleEdit = () => {
  // Get seasonId from Router params
  const { seasonId } = useParams();
  const { state, dispatch } = useSchedule();
  // Use validation hook instead of custom state
  const validation = useScheduleValidation(state, true, false); // showValidation=true, initialShowSaveButton=false
  // Schedule editing uses table view by default
  const [useSimpleView, setUseSimpleView] = useState(false);
  const hasScrolledRef = useRef(false);
  
  // Keep a local state for tracking if validation passed (for button state)
  const [validationPassed, setValidationPassed] = useState(false);


  // Reset change tracking when component mounts to prevent stale state
  useEffect(() => {
    // Clear any leftover change tracking from previous sessions
    dispatch({ type: RESET_CHANGE_TRACKING });
    
    // Also reset any validation state using the hook
    validation.resetValidationState(false);
    setValidationPassed(false);
    
    // Reset scroll tracking
    hasScrolledRef.current = false;
  }, [dispatch]);

  // Clear validation results when schedule changes are made (only triggers on actual changes, not on validation appearing)
  useEffect(() => {
    // Only clear validation if we have results
    if (validation.validationResults) {
      validation.clearValidationResults();
      setValidationPassed(false);
    }
  }, [state.changedGames, state.newGames, state.validationAffectingChanges, state.weeks]); // Note: validation.validationResults is NOT in dependencies

  // Note: Removed scroll to validation results for schedule editing mode
  // Users are actively editing and don't want to be jumped around

  useEffect(() => {
    // Fetch schedule data when component mounts
    const fetchScheduleData = async () => {
      dispatch({ type: SET_LOADING, payload: true });

      try {
        const response = await fetch(`/scheduler/api/seasons/${seasonId}/`);

        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
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


  // Use the validation hook's function, but sync with local state
  const validateSchedule = async () => {
    await validation.validateSchedule();
    // Update local validation passed state based on hook results
    setValidationPassed(validation.showSaveButton);
  };
  
  // Sync local validation state when hook state changes
  useEffect(() => {
    setValidationPassed(validation.showSaveButton);
  }, [validation.showSaveButton]);


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
      
      // Debug logging for schedule edit
      console.log('ScheduleEdit handleSaveChanges - received scheduleData:', {
        gameAssignments: gameAssignments.length,
        weekDates: weekDates.length,
        weekDatesData: weekDates,
        offWeeks: scheduleOffWeeks.length,
        offWeeksData: scheduleOffWeeks
      });
      
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
        isOffWeek: week.is_off_week,
        title: week.title,
        description: week.description,
        has_basketball: week.has_basketball,
        start_time: week.start_time,
        end_time: week.end_time
      }));

      offWeeks = scheduleOffWeeks.map(week => ({
        week_id: week.week_number,
        week_number: week.week_number,
        date: week.monday_date,
        title: week.title,
        description: week.description,
        has_basketball: week.has_basketball
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
          isOffWeek: !!weekData.isOffWeek,
          title: weekData.title,
          description: weekData.description,
          has_basketball: weekData.has_basketball,
          start_time: weekData.start_time,
          end_time: weekData.end_time
        });
        
        if (weekData.isOffWeek) {
          offWeeks.push({
            week_id: weekData.week_number,
            week_number: weekData.week_number,
            date: weekData.monday_date,
            title: weekData.title,
            description: weekData.description,
            has_basketball: weekData.has_basketball,
            start_time: weekData.start_time,
            end_time: weekData.end_time
          });
        }
      }
    }

    try {

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
            disabled={validation.isValidating}
          >
            {validation.isValidating ? (
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
      {validation.validationResults && (
        <div className="mb-4 validation-results">
          <ValidationResults
            validationResults={validation.validationResults}
            ignoredFailures={validation.ignoredFailures}
            onIgnoreFailure={validation.handleIgnoreFailure}
            allPassedOrIgnored={validation.showSaveButton}
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