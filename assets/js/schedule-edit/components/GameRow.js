import React, { useState } from 'react';
import { useSchedule } from '../hooks/useSchedule';
import { UPDATE_GAME, MARK_CHANGED, DELETE_GAME } from '../contexts/ScheduleContext';

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
  
  // Check if this game has been changed
  const isChanged = state.changedGames.has(game.id) || state.newGames.has(game.id);
  
  const handleChange = (field, value) => {
    // Update the game in the state
    dispatch({
      type: UPDATE_GAME,
      payload: { gameId: game.id, field, value }
    });
    
    // Mark the game as changed (if it's not a new game, which is already tracked)
    if (!state.newGames.has(game.id)) {
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
    // Toggle isDeleted flag (handled in reducer)
    dispatch({
      type: DELETE_GAME,
      payload: { gameId: game.id, weekId }
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
          {state.courts.map(court => (
            <option key={court} value={court}>
              {court}
            </option>
          ))}
          {game.court && !state.courts.includes(game.court) && (
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
          {state.levels.map(level => (
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
          {game.level_id && state.teamsByLevel[game.level_id] ? (
            state.teamsByLevel[game.level_id].map(team => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))
          ) : (
            <option value="" disabled>
              {game.level_id ? 'No teams in level' : 'Select level first'}
            </option>
          )}
        </select>
      </td>
      
      {/* Score */}
      <td className="text-center">
        <input 
          type="number"
          name={`score1_${game.id}`}
          className="form-control form-control-sm score-input schedule-input"
          value={game.team1_score || ''}
          onChange={(e) => handleChange('team1_score', e.target.value)}
          min="0"
          placeholder="S1"
        />
        <span className="vs-separator">-</span>
        <input 
          type="number"
          name={`score2_${game.id}`}
          className="form-control form-control-sm score-input schedule-input"
          value={game.team2_score || ''}
          onChange={(e) => handleChange('team2_score', e.target.value)}
          min="0"
          placeholder="S2"
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
          {game.level_id && state.teamsByLevel[game.level_id] ? (
            state.teamsByLevel[game.level_id].map(team => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))
          ) : (
            <option value="" disabled>
              {game.level_id ? 'No teams in level' : 'Select level first'}
            </option>
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
          {game.level_id && state.teamsByLevel[game.level_id] ? (
            state.teamsByLevel[game.level_id].map(team => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))
          ) : (
            <option value="" disabled>
              {game.level_id ? 'No teams in level' : 'Select level first'}
            </option>
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
            className={`btn btn-sm ${isDeleted ? 'btn-success' : 'btn-danger'}`}
            title={isDeleted ? "Restore Game" : "Delete Game"}
            onClick={handleToggleDelete}
          >
            <i className={`fas ${isDeleted ? 'fa-undo' : 'fa-times'}`}></i>
            {isDeleted ? ' Restore' : ''}
          </button>
        )}
      </td>
    </tr>
  );
};

export default GameRow;