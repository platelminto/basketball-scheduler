import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SCHEDULE_DATA, SET_ERROR } from '../contexts/ScheduleContext';

// Placeholder component for the Schedule Create page
// This will be fully implemented based on create_season.html
const ScheduleCreate = () => {
  const { dispatch } = useSchedule();
  const navigate = useNavigate();
  const [scheduleData, setScheduleData] = useState({
    weeks: []
  });
  
  // This will be the form submission handler
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Store the schedule data in context and navigate to team setup
    dispatch({ type: SET_SCHEDULE_DATA, payload: scheduleData });
    navigate('/team_setup');
  };
  
  return (
    <div className="container mt-4">
      <h2>Create Season</h2>
      <p>This page will be implemented to match the create_season.html template</p>
      <button className="btn btn-primary" onClick={handleSubmit}>Continue to Team Setup (Placeholder)</button>
    </div>
  );
};

export default ScheduleCreate;