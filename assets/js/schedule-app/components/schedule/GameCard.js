import React, { useState } from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { UPDATE_GAME, MARK_CHANGED, DELETE_GAME } from '../../contexts/ScheduleContext';

const GameCard = ({ game, weekId }) => {
  const { state, dispatch } = useSchedule();
  
  // Check if this week has multiple days
  const weekData = state.weeks[weekId];
  const uniqueDays = new Set(
    weekData.games
      .filter(g => !g.isDeleted && g.day_of_week !== undefined && g.day_of_week !== null)
      .map(g => g.day_of_week)
  );
  const hasMultipleDays = uniqueDays.size > 1;
  const [score1Error, setScore1Error] = useState(false);
  const [score2Error, setScore2Error] = useState(false);
  
  // Check if this week is locked for score editing
  const isWeekLocked = state.lockedWeeks.has(weekId);
  
  // Check if this game has been changed
  const isChanged = state.changedGames && state.changedGames.has(game.id) || 
                   (state.newGames && state.newGames.has(game.id));
  
  const handleChange = (field, value) => {
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

  // Get team names
  const getTeamName = (teamId) => {
    if (!teamId || !game.level_id || !state.teamsByLevel || !state.teamsByLevel[game.level_id]) {
      return 'TBD';
    }
    const team = state.teamsByLevel[game.level_id].find(t => t.id === teamId);
    return team ? team.name : 'TBD';
  };

  // Get level name
  const getLevelName = () => {
    if (!game.level_id || !state.levels) return '';
    const level = state.levels.find(l => l.id === game.level_id);
    return level ? level.name : '';
  };

  // Check if the game is marked as deleted
  const isDeleted = game.isDeleted;
  
  // Format day name
  const getDayName = () => {
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    return game.day_of_week !== undefined && game.day_of_week !== null 
      ? days[game.day_of_week] 
      : '';
  };

  // Get referee name
  const getRefereeName = () => {
    if (game.referee_name) return game.referee_name;
    if (game.referee_team_id && game.level_id && state.teamsByLevel && state.teamsByLevel[game.level_id]) {
      const team = state.teamsByLevel[game.level_id].find(t => t.id === game.referee_team_id);
      return team ? team.name : '';
    }
    return '';
  };

  return (
    <div className={`game-card ${isChanged ? 'changed' : ''} ${isDeleted ? 'deleted' : ''}`}>
      <div className="game-card-teams">
        <span className="team team1">{getTeamName(game.team1_id)}</span>
        <span className="vs">vs</span>
        <span className="team team2">{getTeamName(game.team2_id)}</span>
      </div>
      
      <div className="game-card-scores">
        <input 
          type="text"
          className={`score-input ${score1Error ? 'is-invalid' : ''}`}
          value={game.team1_score || ''}
          onChange={(e) => {
            const value = e.target.value;
            if (value === '' || /^\d+$/.test(value)) {
              handleChange('team1_score', value);
              setScore1Error(false);
            } else {
              setScore1Error(true);
              setTimeout(() => setScore1Error(false), 1500);
            }
          }}
          onBlur={() => setScore1Error(false)}
          placeholder=""
          disabled={state.editingEnabled || isWeekLocked}
        />
        <span className="score-separator">-</span>
        <input 
          type="text"
          className={`score-input ${score2Error ? 'is-invalid' : ''}`}
          value={game.team2_score || ''}
          onChange={(e) => {
            const value = e.target.value;
            if (value === '' || /^\d+$/.test(value)) {
              handleChange('team2_score', value);
              setScore2Error(false);
            } else {
              setScore2Error(true);
              setTimeout(() => setScore2Error(false), 1500);
            }
          }}
          onBlur={() => setScore2Error(false)}
          placeholder=""
          disabled={state.editingEnabled || isWeekLocked}
        />
      </div>
      
      <div className="game-card-info">
        {hasMultipleDays && getDayName() + ' '}{game.time} • {game.court}{getRefereeName() && ` • Ref: ${getRefereeName()}`}
      </div>
    </div>
  );
};

export default GameCard;