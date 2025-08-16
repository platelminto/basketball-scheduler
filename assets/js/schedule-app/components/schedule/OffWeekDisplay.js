import React from 'react';
import { useSchedule } from '../../hooks/useSchedule';
import { DELETE_WEEK, UPDATE_WEEK_DATE } from '../../contexts/ScheduleContext';

const OffWeekDisplay = ({ weekData, mode = 'score-edit' }) => {
  const { dispatch } = useSchedule();

  const handleDeleteWeek = () => {
    if (mode !== 'create' && mode !== 'schedule-edit') return;
    
    dispatch({
      type: DELETE_WEEK,
      payload: { weekId: weekData.week_number }
    });
  };

  const handleFieldUpdate = (field, value) => {
    if (mode !== 'create' && mode !== 'schedule-edit') return;
    
    dispatch({
      type: UPDATE_WEEK_DATE,
      payload: { 
        weekId: weekData.week_number, 
        field, 
        value 
      }
    });
  };

  const handleTitleSelect = (selectedTitle) => {
    // Set the title based on selection
    let newTitle = selectedTitle;
    let newDescription = weekData.description || '';
    let hasBasketball = weekData.has_basketball || false;
    
    // Set defaults based on selection
    switch(selectedTitle) {
      case 'Off Week':
        newDescription = 'No games scheduled';
        hasBasketball = false;
        break;
      case 'Tournament':
        newDescription = '';
        hasBasketball = true;
        break;
      case 'custom':
        newTitle = ''; // Clear for custom input
        newDescription = '';
        // Keep existing basketball value
        break;
    }
    
    // Update all fields
    dispatch({
      type: UPDATE_WEEK_DATE,
      payload: { 
        weekId: weekData.week_number, 
        field: 'title', 
        value: newTitle 
      }
    });
    
    dispatch({
      type: UPDATE_WEEK_DATE,
      payload: { 
        weekId: weekData.week_number, 
        field: 'description', 
        value: newDescription 
      }
    });
    
    dispatch({
      type: UPDATE_WEEK_DATE,
      payload: { 
        weekId: weekData.week_number, 
        field: 'has_basketball', 
        value: hasBasketball 
      }
    });
  };

  const getAlertClass = () => {
    if (weekData.has_basketball) {
      return 'alert alert-info'; // Blue for basketball events
    }
    return 'alert alert-warning'; // Orange for no basketball
  };

  const getIcon = () => {
    if (weekData.has_basketball) {
      return <i className="fas fa-basketball-ball me-2"></i>;
    }
    return <i className="fas fa-calendar-times me-2"></i>;
  };

  const isEditable = mode === 'create' || mode === 'schedule-edit';

  return (
    <div className="off-week-display mb-3">
      <div className={`${getAlertClass()} p-4`}>
        {/* Header with title, date, and delete button */}
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div className="flex-grow-1 d-flex align-items-center justify-content-center gap-3">
            <h4 className="mb-0">
              {getIcon()}
              <strong>Non-League Week</strong>
            </h4>
            {isEditable && (
              <input 
                type="date"
                className="form-control"
                style={{ width: '160px' }}
                value={weekData.monday_date || ''}
                onChange={(e) => handleFieldUpdate('monday_date', e.target.value)}
              />
            )}
            {!isEditable && (
              <span className="text-muted">- {weekData.monday_date}</span>
            )}
          </div>
          
          {isEditable && (
            <button
              type="button"
              className="btn btn-sm btn-outline-danger"
              title="Delete this non-league week"
              onClick={handleDeleteWeek}
            >
              <i className="fas fa-trash"></i>
            </button>
          )}
        </div>

        {/* Editable fields or display */}
        {isEditable ? (
          <div className="row g-3">
            <div className="col-md-3">
              <label className="form-label">Quick Select</label>
              <select 
                className="form-select"
                value={weekData.title === 'Off Week' ? 'Off Week' : weekData.title === 'Tournament' ? 'Tournament' : 'custom'}
                onChange={(e) => handleTitleSelect(e.target.value)}
              >
                <option value="Off Week">Off Week</option>
                <option value="Tournament">Tournament</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            
            {(weekData.title !== 'Off Week' && weekData.title !== 'Tournament') && (
              <div className="col-md-3">
                <label className="form-label">Title</label>
                <input 
                  type="text"
                  className="form-control"
                  value={weekData.title || ''}
                  onChange={(e) => handleFieldUpdate('title', e.target.value)}
                  placeholder="Enter title"
                />
              </div>
            )}
            
            <div className={(weekData.title !== 'Off Week' && weekData.title !== 'Tournament') ? 'col-md-6' : 'col-md-9'}>
              <label className="form-label">Description</label>
              <input 
                type="text"
                className="form-control"
                value={weekData.description || ''}
                onChange={(e) => handleFieldUpdate('description', e.target.value)}
                placeholder={weekData.title === 'Tournament' 
                  ? "e.g., Charity Tournament, Vacation Tournament, Tournament 2" 
                  : "Describe what's happening this week"}
                style={{ padding: '12px' }}
              />
            </div>
            
            <div className="col-md-12">
              <div className="form-check">
                <input 
                  className="form-check-input"
                  type="checkbox"
                  id={`basketball-${weekData.week_number}`}
                  checked={weekData.has_basketball || false}
                  onChange={(e) => handleFieldUpdate('has_basketball', e.target.checked)}
                />
                <label className="form-check-label" htmlFor={`basketball-${weekData.week_number}`}>
                  Basketball events happening this week (affects color styling)
                </label>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center">
            <div className="h5 mb-1">{weekData.description || 'No description provided'}</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OffWeekDisplay;