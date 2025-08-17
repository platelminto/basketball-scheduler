import React from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { ADD_OFF_WEEK, ADD_NEW_WEEK, COPY_WEEK } from '../../contexts/ScheduleContext';
import { createNewWeek, findLastNormalWeek } from '../../utils/weekUtils';

const WeekSeparator = ({ afterWeekNumber, beforeWeekNumber, mode = 'create' }) => {
  const { state, dispatch } = useSchedule();

  // Helper function to scroll to the WeekSeparator after the newly created week
  const scrollToWeekSeparator = (newWeekNumber) => {
    // Use setTimeout to ensure the DOM has updated after the state change
    setTimeout(() => {
      // Find the WeekSeparator after the newly created week
      const weekSeparators = document.querySelectorAll('.week-separator');
      
      // The separator after week N would be at index N (0-based, since separator before first week is index 0)
      if (weekSeparators[newWeekNumber]) {
        weekSeparators[newWeekNumber].scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
      }
    }, 100);
  };

  const handleAddNonLeague = () => {
    if (mode !== 'create' && mode !== 'schedule-edit') return;
    
    // Calculate where this week will be inserted to determine scroll position
    const sortedWeeks = Object.values(state.weeks).sort((a, b) => a.week_number - b.week_number);
    let insertionIndex;
    if (afterWeekNumber === null) {
      insertionIndex = 0;
    } else {
      const afterWeekIndex = sortedWeeks.findIndex(w => w.week_number === afterWeekNumber);
      insertionIndex = afterWeekIndex !== -1 ? afterWeekIndex + 1 : sortedWeeks.length;
    }
    const newWeekNumber = insertionIndex + 1;
    
    // Calculate the appropriate date for the off week
    let offWeekDate;
    
    if (afterWeekNumber === null) {
      // Inserting at the beginning - use one week before the first week
      if (beforeWeekNumber && state.weeks[beforeWeekNumber]) {
        const beforeWeekDate = new Date(state.weeks[beforeWeekNumber].monday_date);
        const prevWeekDate = new Date(beforeWeekDate);
        prevWeekDate.setDate(beforeWeekDate.getDate() - 7);
        offWeekDate = prevWeekDate.toISOString().split('T')[0];
      } else {
        // Fallback: use current date
        const currentDate = new Date();
        // Adjust to Monday if not already
        const dayOfWeek = currentDate.getDay();
        const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
        currentDate.setDate(currentDate.getDate() + daysUntilMonday);
        offWeekDate = currentDate.toISOString().split('T')[0];
      }
    } else if (beforeWeekNumber === null) {
      // Inserting at the end - use one week after the last week
      if (afterWeekNumber && state.weeks[afterWeekNumber]) {
        const afterWeekDate = new Date(state.weeks[afterWeekNumber].monday_date);
        const nextWeekDate = new Date(afterWeekDate);
        nextWeekDate.setDate(afterWeekDate.getDate() + 7);
        offWeekDate = nextWeekDate.toISOString().split('T')[0];
      } else {
        // Fallback: use current date + 7 days
        const nextWeekDate = new Date();
        nextWeekDate.setDate(nextWeekDate.getDate() + 7);
        offWeekDate = nextWeekDate.toISOString().split('T')[0];
      }
    } else {
      // Inserting between two weeks - the off week should take the date that 
      // the second week currently has, because we'll shift that week later
      const beforeWeekDate = new Date(state.weeks[beforeWeekNumber].monday_date);
      offWeekDate = beforeWeekDate.toISOString().split('T')[0];
    }

    const offWeekData = {
      monday_date: offWeekDate,
      title: 'Off Week',
      description: 'No games scheduled',
      has_basketball: false
    };
    
    dispatch({
      type: ADD_OFF_WEEK,
      payload: { 
        afterWeekId: afterWeekNumber,
        offWeekData
      }
    });
    
    // Scroll to the separator after the newly created week
    scrollToWeekSeparator(newWeekNumber);
  };

  const handleAddNew = () => {
    if (mode !== 'create' && mode !== 'schedule-edit') return;
    
    // Calculate where this week will be inserted to determine scroll position
    const sortedWeeks = Object.values(state.weeks).sort((a, b) => a.week_number - b.week_number);
    let insertionIndex;
    if (afterWeekNumber === null) {
      insertionIndex = 0;
    } else {
      const afterWeekIndex = sortedWeeks.findIndex(w => w.week_number === afterWeekNumber);
      insertionIndex = afterWeekIndex !== -1 ? afterWeekIndex + 1 : sortedWeeks.length;
    }
    const newWeekNumber = insertionIndex + 1;
    
    // Calculate the appropriate date for the new week
    let newWeekDate;
    
    if (afterWeekNumber === null) {
      // Inserting at the beginning - use one week before the first week
      if (beforeWeekNumber && state.weeks[beforeWeekNumber]) {
        const beforeWeekDate = new Date(state.weeks[beforeWeekNumber].monday_date);
        const prevWeekDate = new Date(beforeWeekDate);
        prevWeekDate.setDate(beforeWeekDate.getDate() - 7);
        newWeekDate = prevWeekDate.toISOString().split('T')[0];
      } else {
        // Fallback: use current date
        const currentDate = new Date();
        const dayOfWeek = currentDate.getDay();
        const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
        currentDate.setDate(currentDate.getDate() + daysUntilMonday);
        newWeekDate = currentDate.toISOString().split('T')[0];
      }
    } else if (beforeWeekNumber === null) {
      // Inserting at the end - use one week after the last week
      if (afterWeekNumber && state.weeks[afterWeekNumber]) {
        const afterWeekDate = new Date(state.weeks[afterWeekNumber].monday_date);
        const nextWeekDate = new Date(afterWeekDate);
        nextWeekDate.setDate(afterWeekDate.getDate() + 7);
        newWeekDate = nextWeekDate.toISOString().split('T')[0];
      } else {
        // Fallback: use current date + 7 days
        const nextWeekDate = new Date();
        nextWeekDate.setDate(nextWeekDate.getDate() + 7);
        newWeekDate = nextWeekDate.toISOString().split('T')[0];
      }
    } else {
      // Inserting between two weeks
      const beforeWeekDate = new Date(state.weeks[beforeWeekNumber].monday_date);
      newWeekDate = beforeWeekDate.toISOString().split('T')[0];
    }

    // Create new week using the utility function but with positioned date
    const newWeekData = createNewWeek(state.weeks, null);
    newWeekData.monday_date = newWeekDate;
    
    dispatch({
      type: ADD_NEW_WEEK,
      payload: { 
        afterWeekId: afterWeekNumber,
        newWeekData
      }
    });
    
    // Scroll to the separator after the newly created week
    scrollToWeekSeparator(newWeekNumber);
  };

  const handleCopyAbove = () => {
    if (mode !== 'create' && mode !== 'schedule-edit') return;
    
    // Calculate where this week will be inserted to determine scroll position
    const sortedWeeks = Object.values(state.weeks).sort((a, b) => a.week_number - b.week_number);
    let insertionIndex;
    if (afterWeekNumber === null) {
      insertionIndex = 0;
    } else {
      const afterWeekIndex = sortedWeeks.findIndex(w => w.week_number === afterWeekNumber);
      insertionIndex = afterWeekIndex !== -1 ? afterWeekIndex + 1 : sortedWeeks.length;
    }
    const newWeekNumber = insertionIndex + 1;
    
    // Find the week to copy - prefer the week immediately above, but skip off weeks
    let templateWeek = null;
    
    if (afterWeekNumber && state.weeks[afterWeekNumber] && !state.weeks[afterWeekNumber].isOffWeek) {
      // Copy the week immediately above if it's a regular week
      templateWeek = state.weeks[afterWeekNumber];
    } else {
      // If the week above is an off week or doesn't exist, find any normal week
      templateWeek = findLastNormalWeek(state.weeks);
    }
    
    if (!templateWeek) {
      alert('No regular weeks found to copy. Please add a regular week first.');
      return;
    }
    
    dispatch({
      type: COPY_WEEK,
      payload: { 
        afterWeekId: afterWeekNumber,
        templateWeek
      }
    });
    
    // Scroll to the separator after the newly created week
    scrollToWeekSeparator(newWeekNumber);
  };

  // Only show if in schedule editing mode
  if (mode !== 'create' && mode !== 'schedule-edit') {
    return null;
  }

  return (
    <div className="week-separator text-center my-3">
      <div className="d-flex gap-1 justify-content-center">
        <button
          type="button"
          className="btn btn-sm btn-primary"
          title="Copy the week above"
          onClick={handleCopyAbove}
        >
          Copy Above Week
        </button>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          title="Add a new empty week"
          onClick={handleAddNew}
        >
          Add New Week
        </button>
        <button
          type="button"
          className="btn btn-sm btn-warning"
          title="Add a non-league week"
          onClick={handleAddNonLeague}
        >
          Non-League Week
        </button>
      </div>
    </div>
  );
};

export default WeekSeparator;