import React, { useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, TOGGLE_EDIT_MODE, SET_LOADING, SET_ERROR } from '../contexts/ScheduleContext';
import WeekContainer from '../components/schedule-edit/WeekContainer';

const ScheduleEdit = () => {
  // Get seasonId from Router params
  const { seasonId } = useParams();
  const navigate = useNavigate();
  const { state, dispatch } = useSchedule();

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

  const handleEditToggle = (enabled) => {
    dispatch({ type: TOGGLE_EDIT_MODE, payload: enabled });
  };

  const handleSaveChanges = async () => {
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

    // All games are valid, proceed with save
    const games = [];

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

    // Prepare week date changes
    const weekDateChanges = [];
    Array.from(state.changedWeeks).forEach(weekId => {
      const weekData = state.weeks[weekId];

      if (weekData) {
        weekDateChanges.push({
          id: weekData.id,
          date: weekData.monday_date
        });
      }
    });

    // Use our getCsrfToken function

    try {
      // Log the data being sent
      console.log('Sending data to server:', {
        games,
        week_dates: weekDateChanges
      });

      const response = await fetch(`/scheduler/schedule/${seasonId}/update/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
          games: games,
          week_dates: weekDateChanges
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert(data.message);
        window.location.reload();
      } else {
        alert(`Error: ${data.error || 'Unknown error'}`);
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

        <div className="form-check form-switch align-self-center">
          <input
            className="form-check-input"
            type="checkbox"
            role="switch"
            id="enableScheduleEditToggle"
            checked={state.editingEnabled}
            onChange={(e) => handleEditToggle(e.target.checked)}
          />
          <label className="form-check-label" htmlFor="enableScheduleEditToggle">
            Enable Schedule Editing
          </label>
        </div>

        <div className="d-flex gap-2">
          <Link to="/" className="btn btn-secondary">
            Back to Seasons List
          </Link>
          <button
            type="button"
            className="btn btn-success"
            onClick={handleSaveChanges}
          >
            {state.editingEnabled ? 'Save Schedule Changes' : 'Save Score Changes'}
          </button>
        </div>
      </div>

      {Object.keys(state.weeks).length === 0 ? (
        <p className="alert alert-info">No games found for this season.</p>
      ) : (
        Object.entries(state.weeks).map(([weekNum, weekData]) => (
          <WeekContainer key={weekData.id} weekData={weekData} />
        ))
      )}
    </div>
  );
};

export default ScheduleEdit;