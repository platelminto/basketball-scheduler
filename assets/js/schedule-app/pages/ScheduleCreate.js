import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, SET_ERROR } from '../contexts/ScheduleContext';
import '../styles/schedule-create.css';

const ScheduleCreate = () => {
  const { dispatch } = useSchedule();
  const navigate = useNavigate();
  const [weeks, setWeeks] = useState([]);

  // Add first week by default with today's date
  useEffect(() => {
    if (weeks.length === 0) {
      // Add first week by default with today's date
      const startDate = new Date();
      // Make sure we start on a Monday
      while (startDate.getDay() !== 1) {
        startDate.setDate(startDate.getDate() + 1);
      }
      const formattedDate = formatDate(startDate);

      const newWeek = {
        id: Date.now(),
        weekStartDate: formattedDate,
        isOffWeek: false,
        days: []
      };

      // Add a default day (Monday)
      const newDay = {
        id: Date.now() + Math.random(),
        dayOfWeek: 0, // Monday
        times: []
      };

      // Add default time slots
      [
        { time: '18:10', courts: 2 },
        { time: '19:20', courts: 2 },
        { time: '20:30', courts: 2 },
        { time: '21:40', courts: 3 }
      ].forEach(timeData => {
        newDay.times.push({
          id: Date.now() + Math.random(),
          time: timeData.time,
          courts: timeData.courts
        });
      });

      newWeek.days.push(newDay);
      setWeeks([newWeek]);
    }
  }, []);

  // Helper functions
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
    if (weeks.length === 0) {
      // If no weeks exist, start from next Monday
      const date = new Date();
      while (date.getDay() !== 1) {
        date.setDate(date.getDate() + 1);
      }
      return date;
    }

    // For existing weeks, get the date from the last week (off or not)
    const lastWeek = weeks[weeks.length - 1];
    if (lastWeek.isOffWeek) {
      const date = new Date(lastWeek.weekStartDate);
      date.setDate(date.getDate() + 7);
      return date;
    } else {
      const date = new Date(lastWeek.weekStartDate);
      date.setDate(date.getDate() + 7);
      return date;
    }
  };

  // Week management functions
  const addWeek = (templateWeek = null) => {
    // Default to next Monday if no date provided
    const startDate = findNextWeekDate();
    const formattedDate = formatDate(startDate);

    const newWeek = {
      id: Date.now(), // Unique ID for the week
      weekStartDate: formattedDate,
      isOffWeek: false,
      days: []
    };

    if (templateWeek) {
      // Copy days from template
      newWeek.days = templateWeek.days.map(day => ({
        ...day,
        id: Date.now() + Math.random() // Ensure unique IDs
      }));
    } else {
      // Add a default day (Monday)
      addDay(newWeek, null, startDate);
    }

    setWeeks([...weeks, newWeek]);
  };

  const addOffWeek = () => {
    const startDate = findNextWeekDate();
    const formattedDate = formatDate(startDate);

    const newWeek = {
      id: Date.now(), // Unique ID for the week
      weekStartDate: formattedDate,
      isOffWeek: true
    };

    setWeeks([...weeks, newWeek]);
  };

  const copyLastWeek = () => {
    if (weeks.length === 0) return;

    // Find the last non-off week to use as template
    let lastNonOffWeek = null;
    for (let i = weeks.length - 1; i >= 0; i--) {
      if (!weeks[i].isOffWeek) {
        lastNonOffWeek = weeks[i];
        break;
      }
    }

    if (lastNonOffWeek) {
      addWeek(lastNonOffWeek);
    }
  };

  const deleteWeek = (weekId) => {
    setWeeks(weeks.filter(week => week.id !== weekId));
  };

  // Day management functions
  const addDay = (week, templateDay = null, date = null) => {
    const weekStartDate = new Date(week.weekStartDate);
    
    // Default day selection or copy from template
    let dayIndex = 0; // Monday by default
    
    if (templateDay) {
      // If we're copying from a template day, use its day selection
      dayIndex = templateDay.dayOfWeek;
    } else if (date) {
      dayIndex = date.getDay();
      if (dayIndex === 0) dayIndex = 7; // Sunday as 7 instead of 0
      dayIndex -= 1; // Convert to 0-6 where 0 is Monday
    }

    const newDay = {
      id: Date.now() + Math.random(), // Unique ID for the day
      dayOfWeek: dayIndex,
      times: []
    };

    if (templateDay) {
      // Copy times from template
      newDay.times = templateDay.times.map(time => ({
        ...time,
        id: Date.now() + Math.random() // Ensure unique IDs
      }));
    } else {
      // Add default times with specific courts available
      [
        { time: '18:10', courts: 2 },
        { time: '19:20', courts: 2 },
        { time: '20:30', courts: 2 },
        { time: '21:40', courts: 3 }
      ].forEach(timeData => {
        addTimeSlot(newDay, timeData);
      });
    }

    // Update the week with the new day
    const updatedWeek = {
      ...week,
      days: [...(week.days || []), newDay]
    };

    // Update the weeks state
    setWeeks(weeks.map(w => (w.id === week.id ? updatedWeek : w)));
    return updatedWeek;
  };

  const addDayToWeek = (weekId) => {
    const week = weeks.find(w => w.id === weekId);
    if (!week) return;

    const lastDay = week.days[week.days.length - 1];
    let newDayDate;

    if (lastDay) {
      // Calculate the date for the new day based on the last day's day of week
      const weekStartDate = new Date(week.weekStartDate);
      newDayDate = new Date(weekStartDate);
      newDayDate.setDate(weekStartDate.getDate() + lastDay.dayOfWeek + 1);
    } else {
      // If no days exist yet, add first day (Monday)
      newDayDate = new Date(week.weekStartDate);
    }

    // Create a new day
    const weekStartDate = new Date(week.weekStartDate);
    
    // Determine day of week
    let dayIndex = newDayDate.getDay();
    if (dayIndex === 0) dayIndex = 7; // Sunday as 7 instead of 0
    dayIndex -= 1; // Convert to 0-6 where 0 is Monday

    const newDay = {
      id: Date.now() + Math.random(),
      dayOfWeek: dayIndex,
      times: []
    };

    // Add our standard 4 time slots
    [
      { time: '18:10', courts: 2 },
      { time: '19:20', courts: 2 },
      { time: '20:30', courts: 2 },
      { time: '21:40', courts: 3 }
    ].forEach(timeData => {
      newDay.times.push({
        id: Date.now() + Math.random(),
        time: timeData.time,
        courts: timeData.courts
      });
    });

    // Update the week with the new day
    const updatedWeek = {
      ...week,
      days: [...(week.days || []), newDay]
    };

    // Update the weeks state
    setWeeks(weeks.map(w => (w.id === week.id ? updatedWeek : w)));
  };

  const deleteDay = (weekId, dayId) => {
    const week = weeks.find(w => w.id === weekId);
    if (!week) return;

    const updatedDays = week.days.filter(day => day.id !== dayId);
    const updatedWeek = { ...week, days: updatedDays };

    setWeeks(weeks.map(w => (w.id === weekId ? updatedWeek : w)));
  };

  // Time slot management functions
  const addTimeSlot = (day, defaultValues = null) => {
    const newTime = {
      id: Date.now() + Math.random(), // Unique ID for the time slot
      time: defaultValues?.time || '',
      courts: defaultValues?.courts || 3
    };

    return {
      ...day,
      times: [...day.times, newTime]
    };
  };

  const addTimeSlotToDay = (weekId, dayId) => {
    const week = weeks.find(w => w.id === weekId);
    if (!week) return;

    const day = week.days.find(d => d.id === dayId);
    if (!day) return;
    
    // Default time slot values based on existing slots
    let defaultTime = '';
    let defaultCourts = 2;
    
    // If there are existing time slots, set the new one 70 minutes after the last one
    if (day.times.length > 0) {
      const lastTime = day.times[day.times.length - 1].time;
      if (lastTime && validateTimeFormat(lastTime)) {
        const [hours, minutes] = lastTime.split(':').map(Number);
        let newHours = hours;
        let newMinutes = minutes + 70; // 70 minutes later
        
        if (newMinutes >= 60) {
          newHours += Math.floor(newMinutes / 60);
          newMinutes = newMinutes % 60;
        }
        
        if (newHours > 23) {
          newHours = 23;
          newMinutes = 59;
        }
        
        defaultTime = `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;
      }
      
      // Use 3 courts for the last slot, 2 for others
      if (day.times.length === 3) {
        defaultCourts = 3;
      }
    } else {
      // If no slots yet, start with 18:10
      defaultTime = '18:10';
    }

    const updatedDay = addTimeSlot(day, { time: defaultTime, courts: defaultCourts });
    const updatedDays = week.days.map(d => (d.id === dayId ? updatedDay : d));
    const updatedWeek = { ...week, days: updatedDays };

    setWeeks(weeks.map(w => (w.id === weekId ? updatedWeek : w)));
  };

  const deleteTimeSlot = (weekId, dayId, timeId) => {
    const week = weeks.find(w => w.id === weekId);
    if (!week) return;

    const day = week.days.find(d => d.id === dayId);
    if (!day) return;

    const updatedTimes = day.times.filter(time => time.id !== timeId);
    const updatedDay = { ...day, times: updatedTimes };
    const updatedDays = week.days.map(d => (d.id === dayId ? updatedDay : d));
    const updatedWeek = { ...week, days: updatedDays };

    setWeeks(weeks.map(w => (w.id === weekId ? updatedWeek : w)));
  };

  const updateTimeSlot = (weekId, dayId, timeId, field, value) => {
    const week = weeks.find(w => w.id === weekId);
    if (!week) return;

    const day = week.days.find(d => d.id === dayId);
    if (!day) return;

    const updatedTimes = day.times.map(time => {
      if (time.id === timeId) {
        return { ...time, [field]: value };
      }
      return time;
    });

    const updatedDay = { ...day, times: updatedTimes };
    const updatedDays = week.days.map(d => (d.id === dayId ? updatedDay : d));
    const updatedWeek = { ...week, days: updatedDays };

    setWeeks(weeks.map(w => (w.id === weekId ? updatedWeek : w)));
  };

  // Week date update
  const updateWeekDate = (weekId, date) => {
    setWeeks(weeks.map(week => {
      if (week.id === weekId) {
        return { ...week, weekStartDate: date };
      }
      return week;
    }));
  };

  // Day selection update
  const updateDayOfWeek = (weekId, dayId, dayOfWeek) => {
    const week = weeks.find(w => w.id === weekId);
    if (!week) return;

    const updatedDays = week.days.map(day => {
      if (day.id === dayId) {
        return { ...day, dayOfWeek: parseInt(dayOfWeek) };
      }
      return day;
    });

    const updatedWeek = { ...week, days: updatedDays };
    setWeeks(weeks.map(w => (w.id === weekId ? updatedWeek : w)));
  };

  // Form submission handler
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validate all time inputs
    let isValid = true;
    weeks.forEach(week => {
      if (!week.isOffWeek) {
        week.days.forEach(day => {
          day.times.forEach(time => {
            if (!validateTimeFormat(time.time)) {
              isValid = false;
            }
          });
        });
      }
    });
    
    if (!isValid) {
      alert('Please fix the time format (HH:MM, 24-hour)');
      return;
    }

    // Convert the weeks data for the context
    const scheduleData = {
      weeks: weeks.map((week, idx) => ({
        weekNumber: idx + 1,
        ...week
      }))
    };
    
    // Store the schedule data in context and navigate to team setup
    dispatch({ type: SET_SCHEDULE_DATA, payload: scheduleData });
    navigate('/team_setup');
  };

  // Helper validation function
  const validateTimeFormat = (value) => {
    return /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/.test(value);
  };

  // Render functions for each component type
  const renderOffWeek = (week, index) => (
    <div className="week-container off-week" key={week.id}>
      <div className="week-header">
        <h4>Off Week</h4>
        <div className="d-flex align-items-center">
          <label htmlFor={`off-week-date-${week.id}`} className="me-2">Week Start:</label>
          <input 
            type="date" 
            id={`off-week-date-${week.id}`} 
            className="form-control off-week-date" 
            style={{ width: 'auto' }} 
            value={week.weekStartDate} 
            onChange={(e) => {
              // Force the date to be a Monday
              const selectedDate = new Date(e.target.value);
              const dayOfWeek = selectedDate.getDay();
              if (dayOfWeek !== 1) {
                // Adjust to previous Monday
                const daysToSubtract = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
                selectedDate.setDate(selectedDate.getDate() - daysToSubtract);
                alert('Week start date must be a Monday. Adjusting to ' + formatDate(selectedDate));
              }
              updateWeekDate(week.id, formatDate(selectedDate));
            }}
            required 
          />
        </div>
        <button 
          type="button" 
          className="btn btn-outline-danger btn-sm delete-week-btn"
          onClick={() => deleteWeek(week.id)}
        >
          Delete Week
        </button>
      </div>
      <div className="off-week-text">Off Week ({week.weekStartDate})</div>
    </div>
  );

  const renderRegularWeek = (week, index) => {
    // Count non-off weeks for week numbering
    const weekNum = weeks.filter((w, i) => !w.isOffWeek && i <= index).length;
    
    return (
      <div className="week-container" key={week.id}>
        <div className="week-header">
          <h4>Week {weekNum}</h4>
          <div className="d-flex align-items-center">
            <label htmlFor={`week-start-date-${week.id}`} className="me-2">Week Start:</label>
            <input 
              type="date" 
              id={`week-start-date-${week.id}`} 
              className="form-control week-start-date" 
              style={{ width: 'auto' }} 
              value={week.weekStartDate} 
              onChange={(e) => {
                // Force the date to be a Monday
                const selectedDate = new Date(e.target.value);
                const dayOfWeek = selectedDate.getDay();
                if (dayOfWeek !== 1) {
                  // Adjust to previous Monday
                  const daysToSubtract = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
                  selectedDate.setDate(selectedDate.getDate() - daysToSubtract);
                  alert('Week start date must be a Monday. Adjusting to ' + formatDate(selectedDate));
                }
                updateWeekDate(week.id, formatDate(selectedDate));
              }}
              required 
            />
          </div>
          <button 
            type="button" 
            className="btn btn-outline-danger btn-sm delete-week-btn"
            onClick={() => deleteWeek(week.id)}
          >
            Delete Week
          </button>
        </div>
        <div className="days-container">
          {week.days.map(day => renderDay(week.id, day))}
        </div>
        <button 
          type="button" 
          className="btn btn-outline-primary btn-sm mt-3 add-day-btn"
          onClick={() => addDayToWeek(week.id)}
        >
          + Add Day
        </button>
      </div>
    );
  };

  const renderDay = (weekId, day) => {
    const weekStartDate = weeks.find(w => w.id === weekId)?.weekStartDate;
    const dayDate = new Date(weekStartDate);
    dayDate.setDate(dayDate.getDate() + day.dayOfWeek);
    const formattedDate = formatDate(dayDate);
    
    return (
      <div className="day-container" key={day.id}>
        <div className="day-header">
          <div className="d-flex align-items-center gap-2">
            <select 
              className="form-select day-select" 
              style={{ width: 'auto' }} 
              value={day.dayOfWeek} 
              onChange={(e) => updateDayOfWeek(weekId, day.id, e.target.value)}
              required
            >
              <option value="0">Monday</option>
              <option value="1">Tuesday</option>
              <option value="2">Wednesday</option>
              <option value="3">Thursday</option>
              <option value="4">Friday</option>
              <option value="5">Saturday</option>
              <option value="6">Sunday</option>
            </select>
            <span className="text-muted date-display">{formattedDate}</span>
          </div>
          <button 
            type="button" 
            className="btn btn-outline-danger btn-sm delete-day-btn"
            onClick={() => deleteDay(weekId, day.id)}
          >
            Delete Day
          </button>
        </div>
        <div className="times-header">
          <div style={{ width: '80px' }}>Time</div>
          <div style={{ width: '75px' }}>Courts</div>
        </div>
        <div className="times-container">
          {day.times.map(time => renderTimeSlot(weekId, day.id, time))}
        </div>
        <button 
          type="button" 
          className="btn btn-outline-secondary btn-sm mt-2 add-time-btn"
          onClick={() => addTimeSlotToDay(weekId, day.id)}
        >
          + Add Time Slot
        </button>
      </div>
    );
  };

  const renderTimeSlot = (weekId, dayId, time) => (
    <div className="time-row" key={time.id}>
      <button 
        type="button" 
        className="delete-btn"
        onClick={() => deleteTimeSlot(weekId, dayId, time.id)}
      >
        &times;
      </button>
      <input 
        type="text" 
        className={`form-control time-input ${!validateTimeFormat(time.time) && time.time ? 'invalid' : ''}`} 
        placeholder="18:30" 
        pattern="([0-1][0-9]|2[0-3]):[0-5][0-9]"
        value={time.time} 
        onChange={(e) => {
          const value = e.target.value.replace(/[^0-9:]/g, '').substring(0, 5);
          updateTimeSlot(weekId, dayId, time.id, 'time', value);
        }}
        required
      />
      <input 
        type="number" 
        className="form-control courts-input" 
        placeholder="Courts" 
        min="1" 
        value={time.courts} 
        onChange={(e) => updateTimeSlot(weekId, dayId, time.id, 'courts', parseInt(e.target.value) || '')}
        required
      />
    </div>
  );

  return (
    <div className="container mt-4">
      <h2>Create Season</h2>
      <form id="scheduleForm" className="mt-4" onSubmit={handleSubmit}>
        <div id="weeksContainer">
          {weeks.map((week, index) => 
            week.isOffWeek ? renderOffWeek(week, index) : renderRegularWeek(week, index)
          )}
        </div>
        
        <div className="form-actions">
          <button type="button" className="btn btn-primary" onClick={copyLastWeek}>Copy Above Week</button>
          <button type="button" className="btn btn-outline-secondary" onClick={() => addWeek()}>+ Add New Week</button>
          <button type="button" className="btn btn-secondary" onClick={addOffWeek}>+ Add Off Week</button>
          <button type="submit" className="btn btn-success">Continue to Team Setup</button>
        </div>
      </form>
    </div>
  );
};

export default ScheduleCreate;