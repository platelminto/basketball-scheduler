import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import TeamCourtSetup from '../components/TeamCourtSetup';
import { SET_LOADING, SET_ERROR } from '../contexts/ScheduleContext';

const EditSeasonStructure = () => {
  const { seasonId } = useParams();
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const [seasonData, setSeasonData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Fetch season data when component mounts
  useEffect(() => {
    const fetchSeasonData = async () => {
      setIsLoading(true);
      
      try {
        const response = await fetch(`/scheduler/api/schedule/${seasonId}/`);
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        setSeasonData(data);
      } catch (error) {
        console.error('Error fetching season data:', error);
        dispatch({ type: SET_ERROR, payload: 'Failed to load season data. Please try again.' });
      } finally {
        setIsLoading(false);
      }
    };
    
    if (seasonId) {
      fetchSeasonData();
    }
  }, [seasonId, dispatch]);
  
  // Convert season data to format expected by TeamCourtSetup
  const getCurrentTeamsLevels = () => {
    if (!seasonData || !seasonData.levels || !seasonData.teams_by_level) {
      return { levels: [], courts: [] };
    }
    
    const levels = seasonData.levels.map(level => ({
      id: level.id,
      name: level.name,
      teams: (seasonData.teams_by_level[level.id] || []).map(team => ({
        id: team.id,
        name: team.name
      }))
    }));
    
    const courts = (seasonData.courts || []).map((court, index) => ({
      id: Date.now() + index,
      name: court
    }));
    
    return { levels, courts };
  };
  
  // Handle form submission
  const handleSubmit = async (setupData) => {
    try {
      const response = await fetch(`/scheduler/api/update_teams_levels/${seasonId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(setupData)
      });
      
      const data = await response.json();
      
      if (response.ok) {
        alert('Teams and levels updated successfully!');
        navigate(-1); // Go back to seasons list
      } else {
        alert(`Error updating teams/levels: ${data.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating teams/levels:', error);
      alert(`Network error: ${error.message}`);
    }
  };
  
  // Get CSRF token for form submissions
  const getCsrfToken = () => {
    return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  };
  
  if (isLoading) {
    return (
      <div className="container mt-4">
        <div className="d-flex justify-content-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    );
  }
  
  if (state.error) {
    return (
      <div className="container mt-4">
        <div className="alert alert-danger" role="alert">
          {state.error}
          <button
            className="btn btn-outline-primary ms-3"
            onClick={() => window.location.reload()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mt-4">
      <h2>Edit Teams & Levels: {seasonData?.season?.name}</h2>
      <p className="text-muted">Update the teams and levels for this season.</p>
      
      <TeamCourtSetup
        initialLevels={getCurrentTeamsLevels().levels}
        initialCourts={getCurrentTeamsLevels().courts}
        onSubmit={handleSubmit}
        onCancel={() => navigate(-1)}
        submitButtonText="Update Teams & Levels"
        cancelButtonText="Back to Seasons"
        showCancelButton={true}
        editMode={true}
      />
    </div>
  );
};

export default EditSeasonStructure;