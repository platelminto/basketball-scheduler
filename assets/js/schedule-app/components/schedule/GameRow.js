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
      handleChange('referee_team_id', value);
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
  const rowClass = isDeleted ? 'row-deleted' : (isChanged ? 'row-changed' : '');

  return (
    <tr data-game-id={game.id} className={rowClass}>
      {/* Day of Week */}
      <td>
        <select
          name={`day_${game.id}`}
          className="form-select form-select-sm schedule-input"
          value={game.day_of_week !== undefined && game.day_of_week !== null ? game.day_of_week : ''}
          onChange={(e) => handleChange('day_of_week', e.target.value ? parseInt(e.target.value, 10) : '')}
          disabled={!state.editingEnabled}
          required
        >
          <option value="">---------</option>
          {DAYS_OF_WEEK.map(day => (
            <option key={day.value} value={day.value}>
              {day.label}
            </option>
          ))}
        </select>
      </td>
      
      {/* Time */}
      <td>
        <input 
          type="time"
          name={`time_${game.id}`}
          className="form-control form-control-sm schedule-input"
          value={game.time || ''}
          onChange={(e) => handleChange('time', e.target.value)}
          disabled={!state.editingEnabled}
          required
        />
      </td>
      
      {/* Court */}
      <td>
        <select 
          name={`court_${game.id}`}
          className="form-select form-select-sm schedule-input"
          value={game.court || ''}
          onChange={(e) => handleChange('court', e.target.value)}
          disabled={!state.editingEnabled}
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
      </td>
      
      {/* Level */}
      <td>
        <select 
          name={`level_${game.id}`}
          className="form-select form-select-sm level-select schedule-input"
          value={game.level_id || ''}
          onChange={handleLevelChange}
          disabled={!state.editingEnabled}
        >
          <option value="">---------</option>
          {state.levels && state.levels.map(level => (
            <option key={level.id} value={level.id}>
              {level.name}
            </option>
          ))}
        </select>
      </td>
      
      {/* Team 1 */}
      <td>
        <select 
          name={`team1_${game.id}`}
          className="form-select form-select-sm team-select team1-select schedule-input"
          value={game.team1_id || ''}
          onChange={(e) => handleChange('team1_id', e.target.value)}
          disabled={!state.editingEnabled}
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
          disabled={state.editingEnabled} // Disable score editing when schedule editing is enabled
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
          disabled={state.editingEnabled} // Disable score editing when schedule editing is enabled
        />
      </td>
      
      {/* Team 2 */}
      <td>
        <select 
          name={`team2_${game.id}`}
          className="form-select form-select-sm team-select team2-select schedule-input"
          value={game.team2_id || ''}
          onChange={(e) => handleChange('team2_id', e.target.value)}
          disabled={!state.editingEnabled}
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
      </td>
      
      {/* Referee */}
      <td>
        <select 
          name={`referee_${game.id}`}
          className="form-select form-select-sm team-select ref-select schedule-input"
          value={game.referee_team_id || (showRefereeNameInput ? 'other' : '')}
          onChange={handleRefereeChange}
          disabled={!state.editingEnabled}
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
            disabled={!state.editingEnabled}
          />
        )}
      </td>
      
      {/* Delete/Restore Button */}
      <td className="text-center">
        {state.editingEnabled && (
          <button
            type="button"
            className={`btn btn-sm ${game.id.toString().includes("new_") ? 'btn-danger' : (isDeleted ? 'btn-success' : 'btn-danger')}`}
            title={game.id.toString().includes("new_") ? "Delete Game" : (isDeleted ? "Restore Game" : "Delete Game")}
            onClick={handleToggleDelete}
          >
            <i className={`fas ${game.id.toString().includes("new_") ? 'fa-times' : (isDeleted ? 'fa-undo' : 'fa-times')}`}></i>
            {isDeleted && !game.id.toString().includes("new_") ? ' Restore' : ''}
          </button>
        )}
      </td>
    </tr>
  );
};

export default GameRow;