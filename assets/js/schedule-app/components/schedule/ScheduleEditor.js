import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSchedule } from '../../hooks/useSchedule';
import { useScheduleValidation } from '../../hooks/useScheduleValidation';
import { useRandomFill } from '../../hooks/useRandomFill';
import { ADD_GAME, SET_SCHEDULE_DATA } from '../../contexts/ScheduleContext';
import { createNewWeek, createOffWeek, findLastNormalWeek, createDefaultWeek, scrollToWeek } from '../../utils/weekUtils';
import { collectGameAssignments, collectWeekData } from '../../utils/scheduleDataTransforms';
import WeekContainer from './WeekContainer';
import OffWeekDisplay from './OffWeekDisplay';
import WeekSeparator from './WeekSeparator';
import ValidationResults from './ValidationResults';

const ScheduleEditor = ({ 
  initialData = null, 
  mode = 'create', // 'create', 'schedule-edit', or 'score-edit'
  seasonId = null,
  onSave,
  showValidation = false,
  shouldRandomFill = false,
  onRandomFillComplete = null,
  isDevelopment = false,
  onAutoGenerate = null,
  useSimpleView = false,
}) => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const [renderKey, setRenderKey] = useState(0); // Used to force re-render
  
  // Custom hooks for validation and random fill
  const validation = useScheduleValidation(state, showValidation, mode === 'schedule-edit');
  const randomFill = useRandomFill(state, dispatch);
  
  // Extract validation results for the clearing effect (to match original pattern)
  const validationResults = validation.validationResults;
  
  
  // Clear validation results when schedule changes are made
  useEffect(() => {
    // Only do this if we have validation results
    if (validationResults &&
        (state.changedGames.size > 0 || 
         state.newGames.size > 0 || 
         state.changedWeeks.size > 0 ||
         Object.values(state.weeks).some(week => week.games && week.games.some(game => game.isDeleted)))) {
      
      validation.resetValidationState(mode === 'schedule-edit');
    }
  }, [state.changedGames, state.newGames, state.changedWeeks, state.weeks, mode]);

  // No need for global editing state - components use mode prop


  // Week management functions
  const addWeek = (templateWeek = null) => {
    // Clear validation results since we're making changes
    validation.clearValidationResults();
    
    const newWeek = createNewWeek(state.weeks, templateWeek);
    const nextWeekNum = newWeek.week_number;
    
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
    scrollToWeek(nextWeekNum);
  };
  
  const addOffWeek = () => {
    // Clear validation results since we're making changes
    validation.clearValidationResults();
    
    const newWeek = createOffWeek(state.weeks);
    const nextWeekNum = newWeek.week_number;
    
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
    scrollToWeek(nextWeekNum);
  };
  
  const copyLastWeek = () => {
    const lastNormalWeek = findLastNormalWeek(state.weeks);
    
    // If no normal weeks found, show alert
    if (!lastNormalWeek) {
      alert('No regular weeks found to copy. Please add a regular week first.');
      return;
    }
    
    // Use the last non-off week as a template for the new week
    // addWeek will handle clearing validation results
    addWeek(lastNormalWeek);
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
  
  const handleSave = async (event) => {
    // Prevent default form submission if this is a form event
    if (event && event.preventDefault) {
      event.preventDefault();
    }
    
    if (mode === 'create') {
      // For create mode, validate before saving
      if (showValidation && !validation.showSaveButton) {
        await validation.validateSchedule();
        if (!validation.showSaveButton) {
          alert('Please fix validation errors or ignore them before saving.');
          return;
        }
      }
    }
    
    // Collect the schedule data to pass to the callback
    const gameAssignments = collectGameAssignments(state.weeks);
    const { weekDates, offWeeks } = collectWeekData(state.weeks);
    
    // Call the provided onSave callback with the collected data
    if (onSave) {
      onSave({
        gameAssignments,
        weekDates,
        offWeeks
      });
    }
  };

  // Handle random fill with validation clearing
  const handleRandomFill = () => {
    validation.clearValidationResults();
    randomFill.randomFillSchedule();
    // Force a re-render to reflect the changes
    setRenderKey(prev => prev + 1);
  };
  
  // Respond to shouldRandomFill prop change
  useEffect(() => {
    if (shouldRandomFill && !randomFill.isRandomFilling) {
      // Schedule a random fill, then notify parent when done
      handleRandomFill();
      if (onRandomFillComplete) {
        // This needs to happen after the state update, so use setTimeout to ensure it happens in the next tick
        setTimeout(() => {
          onRandomFillComplete();
        }, 0);
      }
    }
  }, [shouldRandomFill]);

  // Scroll to validation results when they appear
  useEffect(() => {
    if (validationResults && showValidation) {
      // Add a small delay to ensure the validation results are fully rendered
      setTimeout(() => {
        const validationElement = document.querySelector('.validation-results');
        if (validationElement) {
          validationElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start',
            inline: 'nearest' 
          });
        }
      }, 100);
    }
  }, [validationResults, showValidation]);
  
  
  // Use the ValidationResults component
  const renderValidationResults = () => {
    if (!validationResults) return null;
    
    return (
      <ValidationResults
        validationResults={validationResults}
        ignoredFailures={validation.ignoredFailures}
        onIgnoreFailure={validation.handleIgnoreFailure}
        allPassedOrIgnored={validation.showSaveButton}
        onValidationChange={() => {/* Don't reset validation state */}}
      />
    );
  };
  
  // Initialize with a default week with Monday and default time slots
  useEffect(() => {
    if (mode === 'create' && Object.keys(state.weeks).length === 0) {
      const defaultWeek = createDefaultWeek();
      
      // Update state with the default week
      const updatedWeeks = {
        [defaultWeek.week_number]: defaultWeek
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
        <div className="weeks-container" key={renderKey}>
          {Object.entries(state.weeks)
            .sort(([a], [b]) => parseInt(a) - parseInt(b)) // Sort by week number
            .map(([weekNum, weekData], index, sortedWeeks) => (
              <React.Fragment key={weekData.id}>
                {/* Add separator before first week (for inserting off-week at beginning) */}
                {index === 0 && (
                  <WeekSeparator 
                    afterWeekNumber={null}
                    beforeWeekNumber={parseInt(weekNum)}
                    mode={mode}
                  />
                )}
                
                {/* Week content */}
                <div className="mb-4">
                  {weekData.isOffWeek ? (
                    <OffWeekDisplay weekData={weekData} mode={mode} />
                  ) : (
                    <WeekContainer weekData={weekData} mode={mode} useSimpleView={useSimpleView} />
                  )}
                </div>
                
                {/* Add separator after each week (except the last one) */}
                {index < sortedWeeks.length - 1 && (
                  <WeekSeparator 
                    afterWeekNumber={parseInt(weekNum)}
                    beforeWeekNumber={parseInt(sortedWeeks[index + 1][0])}
                    mode={mode}
                  />
                )}
                
                {/* Add separator after last week */}
                {index === sortedWeeks.length - 1 && (
                  <WeekSeparator 
                    afterWeekNumber={parseInt(weekNum)}
                    beforeWeekNumber={null}
                    mode={mode}
                  />
                )}
              </React.Fragment>
            ))}
        </div>
      )}
      
      {/* Week management buttons - moved to bottom */}
      {(mode === 'create' || mode === 'schedule-edit') && (
        <div className="week-management-controls mt-4 mb-4">
          <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center">
            {/* Left side - Auto-generate button */}
            <div className="d-flex gap-2">
              {mode === 'create' && isDevelopment && onAutoGenerate && (
                <button 
                  type="button" 
                  className="btn btn-success" 
                  onClick={onAutoGenerate}
                >
                  Auto-generate Schedule
                </button>
              )}
            </div>

            {/* Center - Week management buttons */}
            <div className="d-flex flex-wrap gap-2 justify-content-center">
              <button type="button" className="btn btn-primary" onClick={copyLastWeek}>
                Copy Above Week
              </button>
              <button type="button" className="btn btn-outline-secondary" onClick={() => addWeek()}>
                + Add New Week
              </button>
              <button type="button" className="btn btn-warning" onClick={addOffWeek}>
                + Add Off Week
              </button>
            </div>
            
            {/* Right side - Validate/Save buttons */}
            <div className="d-flex gap-2">
              {mode === 'create' && showValidation && (
                <button 
                  type="button" 
                  className={validation.showSaveButton ? "btn btn-success" : "btn btn-primary"}
                  onClick={validation.showSaveButton ? handleSave : validation.validateSchedule}
                  disabled={validation.isValidating}
                >
                  {validation.isValidating ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Validating...
                    </>
                  ) : (
                    validation.showSaveButton ? 'Save Schedule' : 'Validate Schedule'
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Validation results - moved after buttons */}
      {showValidation && validationResults && (
        <div className="validation-results">
          {renderValidationResults()}
        </div>
      )}
    </div>
  );
};

export default ScheduleEditor;