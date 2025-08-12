import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_TEAMS_DATA } from '../contexts/ScheduleContext';
import TeamCourtSetup from '../components/TeamCourtSetup';
import '../styles/team-setup.css';

const TeamSetup = () => {
  const { dispatch } = useSchedule();
  const navigate = useNavigate();
  
  // Handle form submission
  const handleSubmit = (setupData) => {
    // Store the teams data in context
    dispatch({ type: SET_TEAMS_DATA, payload: setupData });
    
    // Navigate to schedule create
    navigate('/season/create/schedule', { state: { setupData } });
  };
  
  return (
    <div className="container mt-4">
      <h2>Step 1: Team & Court Setup</h2>
      <p className="text-muted">Define the teams and courts before creating your schedule.</p>
      
      <TeamCourtSetup
        onSubmit={handleSubmit}
        onCancel={() => navigate(-1)}
        submitButtonText="Continue to Game Assignment"
        cancelButtonText="Back to Schedule"
        showCancelButton={true}
      />
    </div>
  );
};

export default TeamSetup;