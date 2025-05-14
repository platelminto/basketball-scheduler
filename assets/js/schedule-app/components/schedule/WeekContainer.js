import React, { useState } from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { UPDATE_WEEK_DATE, ADD_GAME } from '../../contexts/ScheduleContext';
import GameRow from './GameRow';

const WeekContainer = ({ weekData }) => {
  const { state, dispatch } = useSchedule();
  const [collapsed, setCollapsed] = useState(false);
  
  const handleDateChange = (e) => {
    const dateStr = e.target.value;
    const validatedDate = validateDate(dateStr);
    
    dispatch({ 
      type: UPDATE_WEEK_DATE, 
      payload: { 
        weekId: weekData.week_number,
        date: validatedDate
      }
    });
    
    // Update all game dates for this week
    const mondayDate = new Date(validatedDate);
    weekData.games.forEach(game => {
      if (game.day_of_week !== undefined && game.day_of_week !== null) {
        const gameDate = new Date(mondayDate);
        gameDate.setDate(mondayDate.getDate() + parseInt(game.day_of_week));
        
        // Dispatch update for each game's date
        dispatch({
          type: 'UPDATE_GAME',
          payload: { 
            gameId: game.id, 
            field: 'date', 
            value: gameDate.toISOString().split('T')[0] 
          }
        });
      }
    });
  };
  
  const validateDate = (dateStr) => {
    // Parse the date
    const date = new Date(dateStr);
    
    // Check if it's valid
    if (isNaN(date.getTime())) {
      return dateStr; // Return original if invalid
    }
    
    // Get the day of week (0=Sunday, 1=Monday, etc.)
    const dayOfWeek = date.getDay();
    
    // If not Monday (1), find the nearest Monday
    if (dayOfWeek !== 1) {
      // Calculate days to adjust to get to Monday
      // If day is Sunday (0), add 1
      // If day is Tuesday (2) through Saturday (6), subtract (dayOfWeek - 1)
      const daysToAdjust = dayOfWeek === 0 ? 1 : -(dayOfWeek - 1);
      
      // Create a new date with the adjustment
      const adjustedDate = new Date(date);
      adjustedDate.setDate(date.getDate() + daysToAdjust);
      
      // Format as YYYY-MM-DD
      const year = adjustedDate.getFullYear();
      const month = String(adjustedDate.getMonth() + 1).padStart(2, '0');
      const day = String(adjustedDate.getDate()).padStart(2, '0');
      
      // Alert the user
      alert(
        'Only Mondays can be selected for week start dates. ' +
        'The date has been adjusted to the nearest Monday: ' +
        `${month}/${day}/${year}`
      );
      
      return `${year}-${month}-${day}`;
    }
    
    return dateStr;
  };
  
  const handleAddGame = () => {
    // Generate a temporary ID for the new game
    const tempGameId = 'new_' + new Date().getTime();
    
    // Create a new game object
    const newGame = {
      id: tempGameId,
      day_of_week: '',
      time: '',
      court: '',
      level_id: '',
      level_name: '',
      team1_id: '',
      team1_name: '',
      team2_id: '',
      team2_name: '',
      team1_score: '',
      team2_score: '',
      referee_team_id: '',
      referee_name: ''
    };
    
    // Add the game to the week
    dispatch({
      type: ADD_GAME,
      payload: { 
        weekId: weekData.week_number,
        game: newGame
      }
    });
  };
  
  return (
    <div className={`week-container ${collapsed ? 'collapsed' : ''} ${weekData.isOffWeek ? 'off-week' : ''}`} data-week-id={weekData.week_number}>
      <div 
        className="week-header" 
        onClick={(e) => {
          // Don't toggle collapse if they clicked on the date input
          if (
            !e.target.closest('.week-date-input') && 
            !e.target.closest('.week-date-display')
          ) {
            setCollapsed(!collapsed);
          }
        }}
      >
        <h3>
          Week {weekData.week_number} - 
          <span className="d-inline-flex align-items-center">
            {!state.editingEnabled ? (
              <span className="week-date-display">
                {new Date(weekData.monday_date).toLocaleDateString('en-GB', { 
                  day: '2-digit', month: '2-digit', year: 'numeric' 
                })}
              </span>
            ) : (
              <input 
                type="date"
                value={weekData.monday_date}
                className="form-control form-control-sm ms-2 week-date-input"
                onChange={handleDateChange}
                disabled={!state.editingEnabled}
              />
            )}
          </span>
          {weekData.isOffWeek && (
            <span className="badge bg-warning ms-3">OFF WEEK</span>
          )}
        </h3>
      </div>
      
      {!collapsed && !weekData.isOffWeek && (
        <div className="week-content">
          <div className="table-responsive">
            <table className="table table-striped table-bordered table-sm">
              <thead className="table-light">
                <tr>
                  <th>Day</th>
                  <th>Time</th>
                  <th>Court</th>
                  <th>Level</th>
                  <th>Team 1</th>
                  <th>Score</th>
                  <th>Team 2</th>
                  <th>Referee</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {weekData.games.map(game => (
                  <GameRow 
                    key={game.id} 
                    game={game}
                    weekId={weekData.week_number}
                  />
                ))}
              </tbody>
              <tfoot>
                <tr className="add-game-row">
                  <td colSpan="9" className="text-center">
                    {state.editingEnabled && (
                      <button 
                        type="button" 
                        className="btn btn-sm btn-primary add-game-btn"
                        onClick={handleAddGame}
                      >
                        <i className="fas fa-plus"></i> Add Game
                      </button>
                    )}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
      
      {!collapsed && weekData.isOffWeek && (
        <div className="week-content">
          <div className="alert alert-warning mt-3 mb-0">
            <strong>This is an off week.</strong> No games are scheduled for this week.
          </div>
        </div>
      )}
    </div>
  );
};

export default WeekContainer;