import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, SET_LOADING, SET_ERROR, RESET_CHANGE_TRACKING } from '../contexts/ScheduleContext';
import ScheduleEditor from '../components/schedule/ScheduleEditor';

const ScoreEdit = () => {
  // Get seasonId from Router params
  const { seasonId } = useParams();
  const { state, dispatch } = useSchedule();
  const [useSimpleView, setUseSimpleView] = useState(() => {
    return window.innerWidth < 768;
  });
  const hasScrolledRef = useRef(false);

  // Reset change tracking when component mounts to prevent stale state
  useEffect(() => {
    // Clear any leftover change tracking from previous sessions
    dispatch({ type: RESET_CHANGE_TRACKING });
    
    // Reset scroll tracking
    hasScrolledRef.current = false;
  }, [dispatch]);

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

  // Scroll to most recent week after initial data loads (only once)
  useEffect(() => {
    if (state.weeks && Object.keys(state.weeks).length > 0 && state.lockedWeeks && !state.isLoading && !hasScrolledRef.current) {
      hasScrolledRef.current = true;
      // Small delay to ensure DOM is rendered
      const scrollTimeout = setTimeout(() => {
        // Find most recent week that has happened (today or in the past)
        const sortedWeeks = Object.values(state.weeks)
          .filter(week => !week.isOffWeek)
          .sort((a, b) => a.week_number - b.week_number);
        
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        let mostRecentHappenedWeek = null;
        for (let i = sortedWeeks.length - 1; i >= 0; i--) {
          const week = sortedWeeks[i];
          const weekDate = new Date(week.monday_date);
          weekDate.setHours(0, 0, 0, 0);
          
          // Only consider weeks that have happened (today or past)
          if (weekDate <= today) {
            mostRecentHappenedWeek = week;
            break;
          }
        }
        
        console.log('Attempting to scroll to week:', mostRecentHappenedWeek?.week_number);
        
        if (mostRecentHappenedWeek) {
          const weekElement = document.querySelector(`[data-week-id="${mostRecentHappenedWeek.week_number}"]`);
          console.log('Found week element:', weekElement);
          
          if (weekElement) {
            const elementTop = weekElement.offsetTop - 100;
            console.log('Scrolling to position:', elementTop);
            
            window.scrollTo({
              top: elementTop,
              behavior: 'smooth'
            });
          } else {
            console.log('Week element not found, trying again...');
            // Try again with a bit more delay
            setTimeout(() => {
              const retryElement = document.querySelector(`[data-week-id="${mostRecentHappenedWeek.week_number}"]`);
              if (retryElement) {
                console.log('Retry scroll successful');
                retryElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }, 200);
          }
        }
      }, 200); // Small delay
      
      // Cleanup timeout on unmount
      return () => clearTimeout(scrollTimeout);
    }
  }, [state.weeks, state.lockedWeeks, state.isLoading]); // Trigger when data is actually loaded

  const handleSaveChanges = async () => {
    // If nothing has changed, show alert and return
    if (state.changedGames.size === 0) {
      alert('No changes detected. Form not submitted.');
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

        // For score editing, we only need to validate that we have valid score values
        // The game structure itself should already be valid
        const hasValidScores = (
          (game.team1_score === null || game.team1_score === undefined || game.team1_score === '' || 
           !isNaN(parseInt(game.team1_score))) &&
          (game.team2_score === null || game.team2_score === undefined || game.team2_score === '' || 
           !isNaN(parseInt(game.team2_score)))
        );

        if (!hasValidScores) {
          invalidGames.push({
            week: weekData.week_number,
            game: game
          });
        }
      });
    }

    // If any games have invalid scores, stop and show an error
    if (invalidGames.length > 0) {
      const errorMsg = `Cannot save: ${invalidGames.length} game(s) have invalid scores.\\n\\n` +
                      invalidGames.map(ig => {
                        const game = ig.game;
                        return `Week ${ig.week}: ${game.team1_name || 'Unknown'} vs ${game.team2_name || 'Unknown'} - Invalid score values`;
                      }).join('\\n');
      alert(errorMsg);
      console.error('Invalid games:', invalidGames);
      return;
    }

    const games = [];

    // Include ALL games from all weeks (not marked for deletion)
    for (const weekNum in state.weeks) {
      const weekData = state.weeks[weekNum];

      weekData.games.forEach(game => {
        // Skip games that are marked for deletion
        if (game.isDeleted) {
          return;
        }

        games.push({
          id: game.id,
          week: weekData.week_number,
          day: game.day_of_week,
          time: game.time,
          court: game.court,
          level: game.level_id,
          team1: game.season_team1_id,
          team2: game.season_team2_id,
          score1: game.team1_score !== null && game.team1_score !== undefined ? String(game.team1_score) : '',
          score2: game.team2_score !== null && game.team2_score !== undefined ? String(game.team2_score) : '',
          referee: game.referee_season_team_id ? String(game.referee_season_team_id) :
                  game.referee_name ? 'name:' + game.referee_name : ''
        });
      });
    }

    try {
      // Log the data being sent
      console.log('Sending score data to server:', { games });

      const response = await fetch(`/scheduler/api/seasons/${seasonId}/schedule/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          games: games,
          week_dates: [], // No week date changes for score editing
          off_weeks: [] // No off week changes for score editing
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
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
        <h2>Update Scores: {state.season?.name}</h2>

        {window.innerWidth >= 768 && (
          <div className="d-flex gap-3 align-items-center">
            <button
              type="button"
              className={`btn btn-sm ${useSimpleView ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setUseSimpleView(!useSimpleView)}
              title="Toggle between simple card view and detailed table view"
            >
              <i className={`fas ${useSimpleView ? 'fa-table' : 'fa-th-large'} me-2`}></i>
              {useSimpleView ? 'Table View' : 'Simple View'}
            </button>
          </div>
        )}

        <div className="d-flex gap-2">
          
          {/* Reset Changes button */}
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
          
          {/* Save Score Changes button */}
          <button
            type="button"
            className="btn btn-success"
            onClick={handleSaveChanges}
          >
            Save Score Changes
          </button>
        </div>
      </div>

      {/* Schedule Editor Component - Score editing mode only */}
      <ScheduleEditor 
        mode="score-edit"
        showValidation={false}
        onSave={null} // Not used in score editing mode
        seasonId={seasonId}
        useSimpleView={useSimpleView}
      />
    </div>
  );
};

export default ScoreEdit;