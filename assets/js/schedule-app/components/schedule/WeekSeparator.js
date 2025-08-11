import React from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { ADD_OFF_WEEK } from '../../contexts/ScheduleContext';

const WeekSeparator = ({ afterWeekNumber, beforeWeekNumber, mode = 'edit' }) => {
  const { state, dispatch } = useSchedule();

  const handleAddOffWeek = () => {
    if (!state.editingEnabled) return;
    
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
      monday_date: offWeekDate
    };
    
    dispatch({
      type: ADD_OFF_WEEK,
      payload: { 
        afterWeekId: afterWeekNumber,
        offWeekData
      }
    });
  };

  // Only show if editing is enabled (always show in create mode)
  if (!state.editingEnabled && mode !== 'create') {
    return null;
  }

  return (
    <div className="week-separator text-center my-3">
      <button
        type="button"
        className="btn btn-sm btn-outline-success"
        title="Add off week here"
        onClick={handleAddOffWeek}
      >
        <i className="fas fa-plus"></i> Add Off Week
      </button>
    </div>
  );
};

export default WeekSeparator;