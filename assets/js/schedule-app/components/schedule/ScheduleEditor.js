import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSchedule } from '../../hooks/useSchedule';
import { TOGGLE_EDIT_MODE, UPDATE_WEEK_DATE, ADD_GAME, SET_SCHEDULE_DATA } from '../../contexts/ScheduleContext';
import WeekContainer from './WeekContainer';
import ValidationResults from './ValidationResults';

const ScheduleEditor = ({ 
  initialData = null, 
  mode = 'create', // 'create' or 'edit'
  seasonId = null,
  onSave,
  showValidation = false
}) => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const [validationResults, setValidationResults] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [ignoredFailures, setIgnoredFailures] = useState(new Set());
  const [showSaveButton, setShowSaveButton] = useState(mode === 'edit');
  
  // Clear validation results when schedule changes are made
  useEffect(() => {
    // Only do this if we have validation results
    if (validationResults && 
        (state.changedGames.size > 0 || 
         state.newGames.size > 0 || 
         state.changedWeeks.size > 0 ||
         Object.values(state.weeks).some(week => week.games && week.games.some(game => game.isDeleted)))) {
      
      setValidationResults(null);
      setIgnoredFailures(new Set());
      setShowSaveButton(mode === 'edit'); // Reset to default state
    }
  }, [state.changedGames, state.newGames, state.changedWeeks, state.weeks, mode]); // Removed validationResults from dependencies

  // Initialize editing mode based on the component mode
  useEffect(() => {
    const isCreating = mode === 'create';
    dispatch({ type: TOGGLE_EDIT_MODE, payload: isCreating ? true : false });
  }, [mode, dispatch]);

  // Helper functions for date handling
  const formatDate = (date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  const getDayName = (date) => {
    return new Date(date).toLocaleDateString('en-US', { weekday: 'long' });
  };

  const findNextWeekDate = () => {
    // Find the last week in the schedule
    const weekNumbers = Object.keys(state.weeks).map(Number);
    if (weekNumbers.length === 0) {
      // If no weeks exist, start from next Monday
      const date = new Date();
      while (date.getDay() !== 1) {
        date.setDate(date.getDate() + 1);
      }
      return date;
    }

    const lastWeekNum = Math.max(...weekNumbers);
    const lastWeek = state.weeks[lastWeekNum];
    
    // Calculate one week after the last week's date
    const date = new Date(lastWeek.monday_date);
    date.setDate(date.getDate() + 7);
    return date;
  };

  // Week management functions
  const addWeek = (templateWeek = null) => {
    // Default to next Monday if no date provided
    const startDate = findNextWeekDate();
    const formattedDate = formatDate(startDate);
    
    const nextWeekNum = Object.keys(state.weeks).length + 1;
    
    const newWeek = {
      id: nextWeekNum,
      week_number: nextWeekNum,
      monday_date: formattedDate,
      games: []
    };
    
    // If using a template, copy games with appropriate modifications
    if (templateWeek) {
      templateWeek.games.forEach(game => {
        if (!game.isDeleted) {
          const newGameId = `new_${Date.now()}_${Math.random()}`;
          const gameClone = {
            ...game,
            id: newGameId,
            team1_score: '',
            team2_score: ''
          };
          newWeek.games.push(gameClone);
        }
      });
    }
    
    // Update state with the new week
    const updatedWeeks = {
      ...state.weeks,
      [nextWeekNum]: newWeek
    };
    
    // Update the context
    dispatch({ 
      type: SET_SCHEDULE_DATA, 
      payload: {
        ...state,
        weeks: updatedWeeks
      }
    });
    
    // Scroll to the newly added week
    setTimeout(() => {
      const weekElement = document.querySelector(`[data-week-id="${nextWeekNum}"]`);
      if (weekElement) {
        weekElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  };
  
  const addOffWeek = () => {
    // Add an empty week marked as an off week
    const startDate = findNextWeekDate();
    const formattedDate = formatDate(startDate);
    
    const nextWeekNum = Object.keys(state.weeks).length + 1;
    
    const newWeek = {
      id: nextWeekNum,
      week_number: nextWeekNum,
      monday_date: formattedDate,
      games: [],
      isOffWeek: true
    };
    
    // Update state with the new week
    const updatedWeeks = {
      ...state.weeks,
      [nextWeekNum]: newWeek
    };
    
    // Update the context
    dispatch({ 
      type: SET_SCHEDULE_DATA, 
      payload: {
        ...state,
        weeks: updatedWeeks
      }
    });
    
    // Scroll to the newly added week
    setTimeout(() => {
      const weekElement = document.querySelector(`[data-week-id="${nextWeekNum}"]`);
      if (weekElement) {
        weekElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  };
  
  const copyLastWeek = () => {
    // Find the last non-off week
    const weekNumbers = Object.keys(state.weeks).map(Number);
    if (weekNumbers.length === 0) return;
    
    // Sort week numbers in descending order
    const sortedWeekNumbers = weekNumbers.sort((a, b) => b - a);
    
    // Find the last non-off week
    let lastNormalWeek = null;
    for (const weekNum of sortedWeekNumbers) {
      const week = state.weeks[weekNum];
      if (!week.isOffWeek) {
        lastNormalWeek = week;
        break;
      }
    }
    
    // If no normal weeks found, show alert
    if (!lastNormalWeek) {
      alert('No regular weeks found to copy. Please add a regular week first.');
      return;
    }
    
    // Use the last non-off week as a template for the new week
    addWeek(lastNormalWeek);
  };
  
  const validateSchedule = async () => {
    if (!showValidation) {
      // Skip validation if not needed
      return;
    }
    
    setIsValidating(true);
    setValidationResults(null);
    
    try {
      // Collect game assignments - similar to GameAssignment component
      const gameAssignments = collectGameAssignments();
      
      // Convert to backend format
      const scheduleData = webToScheduleFormat(gameAssignments);
      
      // Get levels and teams for validation
      const teams = state.teamsByLevel;
      const levels = state.levels.map(level => level.name);
      const teams_per_level = {};
      
      for (const levelId in teams) {
        const level = state.levels.find(l => l.id === levelId);
        if (level) {
          teams_per_level[level.name] = teams[levelId].length;
        }
      }
      
      const minimalConfig = { 
        levels: levels, 
        teams_per_level: teams_per_level 
      };
      
      // Call validation API
      const response = await fetch('/scheduler/validate_schedule/', {
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
    }
    
    setIsValidating(false);
  };
  
  // Helper functions for validation
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
        
        let referee = game.referee_team_id || "";
        if (!referee && game.referee_name) {
          referee = game.referee_name;
        }
        
        gameAssignments.push({
          week: weekData.week_number,
          dayOfWeek: game.day_of_week,
          time: game.time,
          gameIndex: 0, // Will be determined based on time sorting
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
  
  const webToScheduleFormat = (gameAssignments) => {
    // First, group by week
    const weekGroups = {};
    gameAssignments.forEach(game => {
      const weekKey = game.week;
      
      if (!weekGroups[weekKey]) {
        weekGroups[weekKey] = {
          week: weekKey,
          slots: {}
        };
      }
      
      // Group times and create slots
      const timeStr = game.time;
      
      // Find or create slot number for this time
      let slotNum = 1;
      const slots = weekGroups[weekKey].slots;
      
      // Check if this time already has a slot number
      let foundSlot = false;
      for (const slotKey in slots) {
        const gamesInSlot = slots[slotKey];
        if (gamesInSlot.length > 0 && gamesInSlot[0].time === timeStr) {
          slotNum = parseInt(slotKey);
          foundSlot = true;
          break;
        }
      }
      
      // If no slot was found, create a new one with the next number
      if (!foundSlot) {
        slotNum = Object.keys(slots).length + 1;
      }
      
      // Initialize slot if needed
      if (!slots[slotNum]) {
        slots[slotNum] = [];
      }
      
      // Add the game to the slot
      slots[slotNum].push({
        level: game.level,
        teams: [game.team1, game.team2],
        ref: game.referee,
        time: timeStr // Add time for reference
      });
    });
    
    // Convert to array format for backend
    return Object.values(weekGroups);
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

    setShowSaveButton(allPassedOrIgnored);
  };
  
  const handleIgnoreFailure = (testName, isIgnored) => {
    // Create a new Set to ensure state update is detected
    const updatedIgnores = new Set(ignoredFailures);
    
    if (isIgnored) {
      updatedIgnores.add(testName);
    } else {
      updatedIgnores.delete(testName);
    }
    
    setIgnoredFailures(updatedIgnores);
    
    // Directly calculate the new validation state
    let allPassedOrIgnored = true;
    
    if (validationResults) {
      for (const name in validationResults) {
        // A test fails validation if it failed and is not in the updated ignore set
        if (!validationResults[name].passed && !updatedIgnores.has(name)) {
          allPassedOrIgnored = false;
          break;
        }
      }
    }
    
    // Update button state immediately
    setShowSaveButton(allPassedOrIgnored);
  };
  
  const handleAddGame = (weekId) => {
    // Create a new game object
    const tempGameId = 'new_' + Date.now() + Math.random();
    
    const newGame = {
      id: tempGameId,
      day_of_week: 0, // Monday by default
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
      referee_name: '',
      isDeleted: false
    };
    
    // Add the game to the week
    dispatch({
      type: ADD_GAME,
      payload: { 
        weekId,
        game: newGame
      }
    });
  };
  
  const handleSave = async () => {
    if (mode === 'create') {
      // For create mode, validate before saving
      if (showValidation && !showSaveButton) {
        await validateSchedule();
        if (!showSaveButton) {
          alert('Please fix validation errors or ignore them before saving.');
          return;
        }
      }
    }
    
    // Call the provided onSave callback
    if (onSave) {
      onSave();
    }
  };
  
  // Get CSRF token for form submissions
  const getCsrfToken = () => {
    return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  };
  
  // Use the ValidationResults component
  const renderValidationResults = () => {
    if (!validationResults) return null;
    
    return (
      <ValidationResults
        validationResults={validationResults}
        ignoredFailures={ignoredFailures}
        onIgnoreFailure={handleIgnoreFailure}
        allPassedOrIgnored={showSaveButton}
        onValidationChange={(passed) => setShowSaveButton(passed)}
      />
    );
  };
  
  // Initialize with a default week with Monday and default time slots
  useEffect(() => {
    if (mode === 'create' && Object.keys(state.weeks).length === 0) {
      // Default to next Monday for the first week
      const startDate = new Date();
      while (startDate.getDay() !== 1) {
        startDate.setDate(startDate.getDate() + 1);
      }
      const formattedDate = formatDate(startDate);
      
      // Create a new week
      const nextWeekNum = Object.keys(state.weeks).length + 1;
      const newWeek = {
        id: nextWeekNum,
        week_number: nextWeekNum,
        monday_date: formattedDate,
        games: []
      };
      
      // Create a default Monday with specific court counts
      const defaultTimes = [
        { time: '18:10', courts: 2 },
        { time: '19:20', courts: 2 },
        { time: '20:30', courts: 2 },
        { time: '21:40', courts: 3 }
      ];
      
      // Add each default time slot
      defaultTimes.forEach(timeSlot => {
        for (let i = 0; i < timeSlot.courts; i++) {
          const gameId = `new_${Date.now()}_${Math.random()}`;
          const gameDate = new Date(formattedDate);
          
          newWeek.games.push({
            id: gameId,
            day_of_week: 0, // Monday (0-based)
            time: timeSlot.time,
            court: `Court ${i+1}`,
            date: gameDate.toISOString().split('T')[0],
            level_id: '',
            level_name: '',
            team1_id: '',
            team1_name: '',
            team2_id: '',
            team2_name: '',
            team1_score: '',
            team2_score: '',
            referee_team_id: '',
            referee_name: '',
            isDeleted: false
          });
        }
      });
      
      // Update state with the new week
      const updatedWeeks = {
        [nextWeekNum]: newWeek
      };
      
      // Update the context
      dispatch({ 
        type: SET_SCHEDULE_DATA, 
        payload: {
          ...state,
          weeks: updatedWeeks
        }
      });
    }
  }, [mode, state.weeks]);
  
  return (
    <div className="schedule-editor-container">
      {/* Validation results */}
      {showValidation && validationResults && renderValidationResults()}
      
      {/* Schedule content */}
      {Object.keys(state.weeks).length === 0 ? (
        <div className="text-center mt-5 mb-5">
          <p className="alert alert-info">No games found. {mode === 'create' ? 'Add weeks to create your schedule.' : ''}</p>
          
          {mode === 'create' && (
            <button type="button" className="btn btn-primary" onClick={() => addWeek()}>
              + Add First Week
            </button>
          )}
        </div>
      ) : (
        <div className="weeks-container">
          {Object.entries(state.weeks).map(([weekNum, weekData]) => (
            <div key={weekData.id} className="mb-4">
              <WeekContainer weekData={weekData} />
            </div>
          ))}
        </div>
      )}
      
      {/* Week management buttons - moved to bottom */}
      {(mode === 'create' || state.editingEnabled) && (
        <div className="week-management-controls mt-4">
          <div className="d-flex flex-wrap gap-2 justify-content-center">
            <button type="button" className="btn btn-primary" onClick={copyLastWeek}>
              Copy Above Week
            </button>
            <button type="button" className="btn btn-outline-secondary" onClick={() => addWeek()}>
              + Add New Week
            </button>
            <button type="button" className="btn btn-secondary" onClick={addOffWeek}>
              + Add Off Week
            </button>
            
            {/* In create mode, we still show these buttons */}
            {mode === 'create' && (
              <>
                {showValidation && (
                  <button 
                    type="button" 
                    className={showSaveButton ? "btn btn-success" : "btn btn-primary"}
                    onClick={showSaveButton ? handleSave : validateSchedule}
                    disabled={isValidating}
                  >
                    {isValidating ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Validating...
                      </>
                    ) : (
                      showSaveButton ? 'Save Schedule' : 'Validate Schedule'
                    )}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ScheduleEditor;