import React, { useState } from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { UPDATE_GAME, MARK_CHANGED, DELETE_GAME } from '../../contexts/ScheduleContext';

// Day of week options
const DAYS_OF_WEEK = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' }
];

const GameRow = ({ game, weekId }) => {
  const { state, dispatch } = useSchedule();
  const [showRefereeNameInput, setShowRefereeNameInput] = useState(
    !game.referee_team_id && game.referee_name
  );
  const [score1Error, setScore1Error] = useState(false);
  const [score2Error, setScore2Error] = useState(false);
  
  // Check if this week is locked for score editing
  const isWeekLocked = state.lockedWeeks.has(weekId);
  
  // Check if this game has been changed
  const isChanged = state.changedGames && state.changedGames.has(game.id) || 
                   (state.newGames && state.newGames.has(game.id));
  
  const handleChange = (field, value) => {
    // Special handling for day_of_week to update the date
    if (field === 'day_of_week') {
      // Find the week for this game
      let weekData = null;
      let weekId = null;
      
      for (const wId in state.weeks) {
        const week = state.weeks[wId];
        if (week.games.some(g => g.id === game.id)) {
          weekData = week;
          weekId = wId;
          break;
        }
      }
      
      // If we found the week, update the date based on the week's Monday date
      if (weekData && weekData.monday_date) {
        const mondayDate = new Date(weekData.monday_date);
        // Calculate the new date based on day of week (value)
        const newDate = new Date(mondayDate);
        newDate.setDate(mondayDate.getDate() + parseInt(value));
        
        // Update the date along with day_of_week
        dispatch({
          type: UPDATE_GAME,
          payload: { gameId: game.id, field: 'date', value: newDate.toISOString().split('T')[0] }
        });
      }
    }
    
    // Update the game in the state
    dispatch({
      type: UPDATE_GAME,
      payload: { gameId: game.id, field, value }
    });
    
    // Mark the game as changed (if it's not a new game, which is already tracked)
    if (state.newGames && !state.newGames.has(game.id)) {
      dispatch({
        type: MARK_CHANGED,
        payload: game.id
      });
    }
  };
  
  const handleLevelChange = (e) => {
    const levelId = e.target.value;
    
    handleChange('level_id', levelId);
    
    // Clear team selections when level changes
    handleChange('team1_id', '');
    handleChange('team2_id', '');
    handleChange('referee_team_id', '');
  };
  
  const handleRefereeChange = (e) => {
    const value = e.target.value;
    
    if (value === 'other') {
      setShowRefereeNameInput(true);
      handleChange('referee_team_id', '');
    } else {
      setShowRefereeNameInput(false);
      // Preserve the same type as team IDs in the data - check a sample team
      const sampleTeam = game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id] && state.teamsByLevel[game.level_id][0];
      const shouldParseAsInt = sampleTeam && typeof sampleTeam.id === 'number';
      const finalValue = value && shouldParseAsInt ? parseInt(value, 10) : value;
      handleChange('referee_team_id', finalValue);
      handleChange('referee_name', '');
    }
  };
  
  const handleToggleDelete = () => {
    // Check if we're in creation mode (IDs contain "new_")
    const isInCreationMode = game.id.toString().includes("new_");
    
    // Toggle isDeleted flag (handled in reducer)
    dispatch({
      type: DELETE_GAME,
      payload: { 
        gameId: game.id, 
        weekId,
        isCreationMode: isInCreationMode
      }
    });
  };

  // Check if the game is marked as deleted
  const isDeleted = game.isDeleted;
  
  // Build row class - only use changed/deleted states
  let rowClass = '';
  if (isDeleted) {
    rowClass = 'row-deleted';
  } else if (isChanged) {
    rowClass = 'row-changed';
  }

  return (
    <tr data-game-id={game.id} className={rowClass}>
      {/* Day of Week */}
      <td>
        {state.editingEnabled ? (
          <select
            name={`day_${game.id}`}
            className="form-select form-select-sm schedule-input"
            value={game.day_of_week !== undefined && game.day_of_week !== null ? game.day_of_week : ''}
            onChange={(e) => handleChange('day_of_week', e.target.value ? parseInt(e.target.value, 10) : '')}
            required
          >
            <option value="">---------</option>
            {DAYS_OF_WEEK.map(day => (
              <option key={day.value} value={day.value}>
                {day.label}
              </option>
            ))}
          </select>
        ) : (
          <span className="schedule-text-readonly">
            {game.day_of_week !== undefined && game.day_of_week !== null
              ? DAYS_OF_WEEK.find(day => day.value === game.day_of_week)?.label || ''
              : ''}
          </span>
        )}
      </td>
      
      {/* Time */}
      <td>
        {state.editingEnabled ? (
          <input 
            type="time"
            name={`time_${game.id}`}
            className="form-control form-control-sm schedule-input"
            value={game.time || ''}
            onChange={(e) => handleChange('time', e.target.value)}
            required
          />
        ) : (
          <span className="schedule-text-readonly">
            {game.time || ''}
          </span>
        )}
      </td>
      
      {/* Court */}
      <td>
        {state.editingEnabled ? (
          <select 
            name={`court_${game.id}`}
            className="form-select form-select-sm schedule-input"
            value={game.court || ''}
            onChange={(e) => handleChange('court', e.target.value)}
          >
            <option value="">---------</option>
            {state.courts && state.courts.map(court => (
              <option key={court} value={court}>
                {court}
              </option>
            ))}
            {game.court && state.courts && !state.courts.includes(game.court) && (
              <option value={game.court}>(!) {game.court}</option>
            )}
          </select>
        ) : (
          <span className="schedule-text-readonly">
            {game.court || ''}
          </span>
        )}
      </td>
      
      {/* Level */}
      <td>
        {state.editingEnabled ? (
          <select 
            name={`level_${game.id}`}
            className="form-select form-select-sm level-select schedule-input"
            value={game.level_id || ''}
            onChange={handleLevelChange}
          >
            <option value="">---------</option>
            {state.levels && state.levels.map(level => (
              <option key={level.id} value={level.id}>
                {level.name}
              </option>
            ))}
          </select>
        ) : (
          <span className="schedule-text-readonly">
            {game.level_id && state.levels
              ? state.levels.find(level => level.id === game.level_id)?.name || ''
              : ''}
          </span>
        )}
      </td>
      
      {/* Team 1 */}
      <td>
        {state.editingEnabled ? (
          <select 
            name={`team1_${game.id}`}
            className="form-select form-select-sm team-select team1-select schedule-input"
            value={game.team1_id || ''}
            onChange={(e) => {
              const value = e.target.value;
              // Preserve the same type as team IDs in the data - check a sample team
              const sampleTeam = game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id] && state.teamsByLevel[game.level_id][0];
              const shouldParseAsInt = sampleTeam && typeof sampleTeam.id === 'number';
              const finalValue = value && shouldParseAsInt ? parseInt(value, 10) : value;
              handleChange('team1_id', finalValue);
            }}
          >
            <option value="">---------</option>
            {game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id] ? (
              state.teamsByLevel[game.level_id].map(team => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))
            ) : (
              game.level_id ? (
                <option value="" disabled>No teams in level</option>
              ) : (
                <option value="" disabled>Select level first</option>
              )
            )}
          </select>
        ) : (
          <span className="schedule-text-readonly">
            {game.team1_id && game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id]
              ? state.teamsByLevel[game.level_id].find(team => team.id === game.team1_id)?.name || ''
              : ''}
          </span>
        )}
      </td>
      
      {/* Score */}
      <td className="text-center">
        <input 
          type="text"
          name={`score1_${game.id}`}
          className={`form-control form-control-sm score-input schedule-input ${score1Error ? 'is-invalid' : ''}`}
          value={game.team1_score || ''}
          onChange={(e) => {
            // Ensure the value is a valid non-negative integer
            const value = e.target.value;
            if (value === '' || /^\d+$/.test(value)) {
              handleChange('team1_score', value);
              setScore1Error(false);
            } else {
              setScore1Error(true);
              // Show error for 2 seconds then clear the invalid input
              setTimeout(() => {
                setScore1Error(false);
              }, 1500);
            }
          }}
          onBlur={() => setScore1Error(false)}
          min="0"
          pattern="[0-9]*"
          inputMode="numeric"
          placeholder="S1"
          disabled={state.editingEnabled || isWeekLocked} // Disable score editing when schedule editing is enabled or week is locked
        />
        <span className="vs-separator">-</span>
        <input 
          type="text"
          name={`score2_${game.id}`}
          className={`form-control form-control-sm score-input schedule-input ${score2Error ? 'is-invalid' : ''}`}
          value={game.team2_score || ''}
          onChange={(e) => {
            // Ensure the value is a valid non-negative integer
            const value = e.target.value;
            if (value === '' || /^\d+$/.test(value)) {
              handleChange('team2_score', value);
              setScore2Error(false);
            } else {
              setScore2Error(true);
              // Show error for 2 seconds then clear the invalid input
              setTimeout(() => {
                setScore2Error(false);
              }, 1500);
            }
          }}
          onBlur={() => setScore2Error(false)}
          min="0"
          pattern="[0-9]*"
          inputMode="numeric"
          placeholder="S2"
          disabled={state.editingEnabled || isWeekLocked} // Disable score editing when schedule editing is enabled or week is locked
        />
      </td>
      
      {/* Team 2 */}
      <td>
        {state.editingEnabled ? (
          <select 
            name={`team2_${game.id}`}
            className="form-select form-select-sm team-select team2-select schedule-input"
            value={game.team2_id || ''}
            onChange={(e) => {
              const value = e.target.value;
              // Preserve the same type as team IDs in the data - check a sample team
              const sampleTeam = game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id] && state.teamsByLevel[game.level_id][0];
              const shouldParseAsInt = sampleTeam && typeof sampleTeam.id === 'number';
              const finalValue = value && shouldParseAsInt ? parseInt(value, 10) : value;
              handleChange('team2_id', finalValue);
            }}
          >
            <option value="">---------</option>
            {game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id] ? (
              state.teamsByLevel[game.level_id].map(team => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))
            ) : (
              game.level_id ? (
                <option value="" disabled>No teams in level</option>
              ) : (
                <option value="" disabled>Select level first</option>
              )
            )}
          </select>
        ) : (
          <span className="schedule-text-readonly">
            {game.team2_id && game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id]
              ? state.teamsByLevel[game.level_id].find(team => team.id === game.team2_id)?.name || ''
              : ''}
          </span>
        )}
      </td>
      
      {/* Referee */}
      <td>
        {state.editingEnabled ? (
          <>
            <select 
              name={`referee_${game.id}`}
              className="form-select form-select-sm team-select ref-select schedule-input"
              value={game.referee_team_id || (showRefereeNameInput ? 'other' : '')}
              onChange={handleRefereeChange}
            >
              <option value="">---------</option>
              {game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id] ? (
                state.teamsByLevel[game.level_id].map(team => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))
              ) : (
                game.level_id ? (
                  <option value="" disabled>No teams in level</option>
                ) : (
                  <option value="" disabled>Select level first</option>
                )
              )}
              <option value="other">Other...</option>
            </select>
            {showRefereeNameInput && (
              <input 
                type="text"
                name={`referee_name_${game.id}`}
                className="form-control form-control-sm mt-1 ref-other-input schedule-input"
                value={game.referee_name || ''}
                onChange={(e) => handleChange('referee_name', e.target.value)}
                placeholder="Enter referee name"
              />
            )}
          </>
        ) : (
          <span className="schedule-text-readonly">
            {game.referee_team_id && game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id]
              ? state.teamsByLevel[game.level_id].find(team => team.id === game.referee_team_id)?.name || ''
              : game.referee_name || ''}
          </span>
        )}
      </td>
      
      {/* Delete/Restore Button */}
      {state.editingEnabled && (
        <td className="text-center">
          <button
            type="button"
            className={`btn btn-sm ${game.id.toString().includes("new_") ? 'btn-danger' : (isDeleted ? 'btn-success' : 'btn-danger')}`}
            title={game.id.toString().includes("new_") ? "Delete Game" : (isDeleted ? "Restore Game" : "Delete Game")}
            onClick={handleToggleDelete}
          >
            <i className={`fas ${game.id.toString().includes("new_") ? 'fa-times' : (isDeleted ? 'fa-undo' : 'fa-times')}`}></i>
            {isDeleted && !game.id.toString().includes("new_") ? ' Restore' : ''}
          </button>
        </td>
      )}
    </tr>
  );
};

export default GameRow;