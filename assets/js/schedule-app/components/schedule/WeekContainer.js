import React, { useState, useEffect } from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { UPDATE_WEEK_DATE, ADD_GAME, DELETE_WEEK, ADD_OFF_WEEK, TOGGLE_WEEK_LOCK } from '../../contexts/ScheduleContext';
import { getGameWeekNumbers } from '../../utils/weekUtils';
import GameRow from './GameRow';
import GameCard from './GameCard';

const WeekContainer = ({ weekData, mode = 'score-edit', useSimpleView = false }) => {
  const { state, dispatch } = useSchedule();
  
  // Early return for off-weeks - they should be handled by OffWeekDisplay component
  if (weekData.isOffWeek) {
    return null;
  }
  
  // Get game week numbers mapping
  const gameWeekNumbers = getGameWeekNumbers(state.weeks);
  const displayWeekNumber = gameWeekNumbers[weekData.week_number];
  
  // Check if this week is locked
  const isLocked = state.lockedWeeks.has(weekData.week_number);
  
  // Determine if this is the most recent week with incomplete scores
  const isMostRecentIncompleteWeek = () => {
    
    const sortedWeeks = Object.values(state.weeks)
      .filter(week => !week.isOffWeek)
      .sort((a, b) => a.week_number - b.week_number);
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Find the most recent week (today or in the past) that has incomplete scores
    for (let i = sortedWeeks.length - 1; i >= 0; i--) {
      const week = sortedWeeks[i];
      const weekDate = new Date(week.monday_date);
      weekDate.setHours(0, 0, 0, 0);
      
      // Only consider weeks that have happened (today or past)
      if (weekDate > today) continue;
      
      if (week.games.length === 0) continue;
      
      const gamesWithBothScores = week.games.filter(game => 
        !game.isDeleted && 
        (game.team1_score !== null && game.team1_score !== undefined && game.team1_score !== '') && 
        (game.team2_score !== null && game.team2_score !== undefined && game.team2_score !== '')
      ).length;
      
      const totalActiveGames = week.games.filter(game => !game.isDeleted).length;
      const hasIncompleteScores = totalActiveGames > 0 && gamesWithBothScores < totalActiveGames;
      
      if (hasIncompleteScores) {
        return week.week_number === weekData.week_number;
      }
    }
    
    return false;
  };
  
  // Determine if this week should be expanded by default
  const shouldBeExpandedByDefault = () => {
    
    // For schedule-edit mode, don't auto-expand any weeks
    if (mode === 'schedule-edit') return false;
    
    const sortedWeeks = Object.values(state.weeks)
      .filter(week => !week.isOffWeek)
      .sort((a, b) => a.week_number - b.week_number);
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Find the most recent week that has happened (today or past)
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
    
    // If we found a most recent happened week, check if this is it
    if (mostRecentHappenedWeek) {
      return weekData.week_number === mostRecentHappenedWeek.week_number;
    }
    
    // If no week has happened yet, expand the first week
    return sortedWeeks.length > 0 && weekData.week_number === sortedWeeks[0].week_number;
  };

  // In create mode and schedule-edit mode: start all weeks expanded, in other modes: start based on shouldBeExpandedByDefault
  const [collapsed, setCollapsed] = useState((mode === 'create' || mode === 'schedule-edit') ? false : !shouldBeExpandedByDefault());
  
  // Check if this week has incomplete scores (not all games have scores AND week date is before today)
  const hasIncompleteScores = () => {
    if (!weekData.games || weekData.games.length === 0) return false;
    
    // Check if week date is before today
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Reset time to start of day
    const weekDate = new Date(weekData.monday_date);
    weekDate.setHours(0, 0, 0, 0); // Reset time to start of day
    
    if (weekDate >= today) return false; // Don't mark future weeks as incomplete
    
    const gamesWithBothScores = weekData.games.filter(game => 
      !game.isDeleted && 
      (game.team1_score !== null && game.team1_score !== undefined && game.team1_score !== '') && 
      (game.team2_score !== null && game.team2_score !== undefined && game.team2_score !== '')
    ).length;
    
    const totalActiveGames = weekData.games.filter(game => !game.isDeleted).length;
    
    // Return true if not all games have complete scores (both team1 and team2 scores)
    return gamesWithBothScores < totalActiveGames;
  };
  
  // Any locked week can be unlocked
  const canBeUnlocked = () => {
    return isLocked;
  };
  
  const handleLockToggle = (e) => {
    e.stopPropagation(); // Prevent triggering the week collapse/expand
    
    if (isLocked && !canBeUnlocked()) {
      return; // Don't allow unlocking if conditions aren't met
    }
    
    dispatch({
      type: TOGGLE_WEEK_LOCK,
      payload: { weekNumber: weekData.week_number }
    });
  };
  
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

  const handleDeleteWeek = () => {
    if (mode !== 'create' && mode !== 'schedule-edit') return;
    
    const confirmDelete = window.confirm(
      `Are you sure you want to delete Week ${displayWeekNumber}? This will remove all games in this week.`
    );
    
    if (confirmDelete) {
      dispatch({
        type: DELETE_WEEK,
        payload: { weekId: weekData.week_number }
      });
    }
  };

  
  return (
    <div className={`week-container ${collapsed ? 'collapsed' : ''}`} data-week-id={weekData.week_number}>
      <div 
        className="week-header" 
        onClick={(e) => {
          // Don't toggle collapse if they clicked on the date input, buttons, or lock button
          if (
            !e.target.closest('.week-date-input') && 
            !e.target.closest('.week-date-display') &&
            !e.target.closest('.week-actions') &&
            !e.target.closest('.btn')
          ) {
            setCollapsed(!collapsed);
          }
        }}
      >
        <div className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center">
            <h3 className="mb-0 me-3">
              Week {displayWeekNumber} -{' '}
              <span className="d-inline-flex align-items-center">
                {mode === 'score-edit' ? (
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
                    disabled={mode === 'score-edit'}
                  />
                )}
              </span>
              {mode === 'score-edit' && hasIncompleteScores() && (
                <span className="badge bg-warning ms-3" title="Some games missing scores">
                  <i className="fas fa-exclamation-triangle"></i> Missing scores
                </span>
              )}
            </h3>
            
            {/* Lock icon - only show when not in editing mode */}
            {mode === 'score-edit' && (
              <button
                type="button"
                className={`btn btn-sm ${isLocked ? 'btn-outline-danger' : 'btn-outline-success'} me-2`}
                style={{ alignSelf: 'stretch' }}
                title={isLocked ? (canBeUnlocked() ? 'Click to unlock week' : 'Week is locked (unlock previous weeks first)') : 'Click to lock week'}
                onClick={handleLockToggle}
                disabled={isLocked && !canBeUnlocked()}
              >
                <i className={`fas ${isLocked ? 'fa-lock' : 'fa-lock-open'}`}></i>
              </button>
            )}
          </div>
          
          {(mode === 'create' || mode === 'schedule-edit') && (
            <div className="week-actions d-flex gap-2">
              <button
                type="button"
                className="btn btn-sm btn-danger"
                title="Delete this week"
                onClick={handleDeleteWeek}
              >
                <i className="fas fa-trash"></i> Delete Week
              </button>
            </div>
          )}
        </div>
      </div>
      
      {!collapsed && (
        <div className="week-content">
          {useSimpleView && mode === 'score-edit' ? (
            // Simple card view - only when not editing
            <div className="games-cards">
              {weekData.games.map(game => (
                <GameCard 
                  key={game.id} 
                  game={game}
                  weekId={weekData.week_number}
                  mode={mode}
                />
              ))}
            </div>
          ) : (
            // Table view
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
                    {(mode === 'create' || mode === 'schedule-edit') && <th>Action</th>}
                  </tr>
                </thead>
                <tbody>
                  {weekData.games.map(game => (
                    <GameRow 
                      key={game.id} 
                      game={game}
                      weekId={weekData.week_number}
                      mode={mode}
                    />
                  ))}
                </tbody>
                <tfoot>
                  <tr className="add-game-row">
                    <td colSpan={mode === 'create' || mode === 'schedule-edit' ? "9" : "8"} className="text-center">
                      {(mode === 'create' || mode === 'schedule-edit') && (
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
          )}
        </div>
      )}
    </div>
  );
};

export default WeekContainer;