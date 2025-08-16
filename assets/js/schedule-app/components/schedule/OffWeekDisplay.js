import React from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { DELETE_WEEK } from '../../contexts/ScheduleContext';

const OffWeekDisplay = ({ weekData, mode = 'score-edit' }) => {
  const { dispatch } = useSchedule();

  const handleDeleteWeek = () => {
    if (mode !== 'create' && mode !== 'schedule-edit') return;
    
    dispatch({
      type: DELETE_WEEK,
      payload: { weekId: weekData.week_number }
    });
  };

  return (
    <div className="off-week-display mb-3">
      <div className="alert alert-warning d-flex justify-content-between align-items-center">
        <div className="text-center flex-grow-1">
          <strong>Off Week - {weekData.monday_date}</strong>
          <div className="mt-1">No games are scheduled for this week.</div>
        </div>
        
        {(mode === 'create' || mode === 'schedule-edit') && (
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            title="Delete this off week"
            onClick={handleDeleteWeek}
          >
            <i className="fas fa-trash"></i>
          </button>
        )}
      </div>
    </div>
  );
};

export default OffWeekDisplay;