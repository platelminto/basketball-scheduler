import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_TEAMS_DATA, SET_ERROR } from '../contexts/ScheduleContext';
import '../styles/team-setup.css';

const TeamSetup = () => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  
  // Default levels
  const defaultLevels = [
    { id: Date.now() + 1, name: 'Mid', teams: [] },
    { id: Date.now() + 2, name: 'High', teams: [] },
    { id: Date.now() + 3, name: 'Top', teams: [] }
  ];
  
  // Default courts
  const defaultCourts = [
    { id: Date.now() + 4, name: 'Court 1' },
    { id: Date.now() + 5, name: 'Court 2' },
    { id: Date.now() + 6, name: 'Court 3' }
  ];
  
  const [levels, setLevels] = useState(defaultLevels);
  const [courts, setCourts] = useState(defaultCourts);
  
  // Check if schedule data exists in context
  useEffect(() => {
    if (!state.scheduleData) {
      alert('No schedule data found. Please go back and create a schedule first.');
    }
  }, [state.scheduleData]);
  
  // Generate some default teams for each level
  useEffect(() => {
    setLevels(levels.map(level => {
      if (level.teams.length === 0) {
        // Generate 6 default teams for this level
        const defaultTeams = [];
        for (let i = 1; i <= 6; i++) {
          defaultTeams.push({
            id: Date.now() + Math.random(),
            name: `Team ${level.name}${i}`
          });
        }
        return { ...level, teams: defaultTeams };
      }
      return level;
    }));
  }, []);
  
  // Level management functions
  const addLevel = () => {
    const nextLevelNum = levels.length + 1;
    const newLevel = {
      id: Date.now(),
      name: `Level ${nextLevelNum}`,
      teams: []
    };
    setLevels([...levels, newLevel]);
  };
  
  const deleteLevel = (levelId) => {
    if (levels.length <= 1) {
      alert('You must have at least one level');
      return;
    }
    setLevels(levels.filter(level => level.id !== levelId));
  };
  
  const updateLevelName = (levelId, name) => {
    setLevels(levels.map(level => {
      if (level.id === levelId) {
        return { ...level, name };
      }
      return level;
    }));
  };
  
  // Team management functions
  const addTeam = (levelId, defaultName = '') => {
    setLevels(levels.map(level => {
      if (level.id === levelId) {
        return {
          ...level,
          teams: [
            ...level.teams,
            {
              id: Date.now() + Math.random(),
              name: defaultName || ''
            }
          ]
        };
      }
      return level;
    }));
  };
  
  const deleteTeam = (levelId, teamId) => {
    setLevels(levels.map(level => {
      if (level.id === levelId) {
        return {
          ...level,
          teams: level.teams.filter(team => team.id !== teamId)
        };
      }
      return level;
    }));
  };
  
  const updateTeamName = (levelId, teamId, name) => {
    setLevels(levels.map(level => {
      if (level.id === levelId) {
        return {
          ...level,
          teams: level.teams.map(team => {
            if (team.id === teamId) {
              return { ...team, name };
            }
            return team;
          })
        };
      }
      return level;
    }));
  };
  
  // Court management functions
  const addCourt = (defaultName = '') => {
    const nextCourtNum = courts.length + 1;
    setCourts([
      ...courts,
      {
        id: Date.now() + Math.random(),
        name: defaultName || `Court ${nextCourtNum}`
      }
    ]);
  };
  
  const deleteCourt = (courtId) => {
    setCourts(courts.filter(court => court.id !== courtId));
  };
  
  const updateCourtName = (courtId, name) => {
    setCourts(courts.map(court => {
      if (court.id === courtId) {
        return { ...court, name };
      }
      return court;
    }));
  };
  
  // Form submission handler
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Convert levels to the format expected by the next page
    const teamsData = {};
    levels.forEach(level => {
      if (level.name.trim()) {
        teamsData[level.name] = level.teams
          .map(team => team.name.trim())
          .filter(name => name !== '');
      }
    });
    
    // Convert courts to array of names
    const courtNames = courts
      .map(court => court.name.trim())
      .filter(name => name !== '');
    
    // Combine with schedule data
    const combinedData = {
      schedule: state.scheduleData || {},
      teams: teamsData,
      courts: courtNames
    };
    
    // Store the teams data in context and navigate to game assignment
    dispatch({ type: SET_TEAMS_DATA, payload: combinedData });
    navigate('/game_assignment');
  };
  
  // Render functions
  const renderLevelColumn = (level) => (
    <div className="level-column" key={level.id}>
      <div className="level-header">
        <input 
          type="text" 
          className="level-name-input form-control" 
          value={level.name} 
          onChange={(e) => updateLevelName(level.id, e.target.value)}
          required
        />
        <button 
          type="button" 
          className="btn btn-outline-danger btn-sm delete-level-btn"
          onClick={() => deleteLevel(level.id)}
        >
          ×
        </button>
      </div>
      <div className="teams-container">
        {level.teams.map(team => renderTeamRow(level.id, team))}
      </div>
      <button 
        type="button" 
        className="btn btn-outline-secondary btn-sm mt-2 add-team-btn"
        onClick={() => addTeam(level.id)}
      >
        + Add Team
      </button>
    </div>
  );
  
  const renderTeamRow = (levelId, team) => (
    <div className="team-row" key={team.id}>
      <button 
        type="button" 
        className="delete-btn"
        onClick={() => deleteTeam(levelId, team.id)}
      >
        &times;
      </button>
      <input 
        type="text" 
        className="form-control team-input" 
        placeholder="Team Name" 
        value={team.name}
        onChange={(e) => updateTeamName(levelId, team.id, e.target.value)}
        required
      />
    </div>
  );
  
  const renderCourtRow = (court) => (
    <div className="team-row" key={court.id}>
      <button 
        type="button" 
        className="delete-btn"
        onClick={() => deleteCourt(court.id)}
      >
        &times;
      </button>
      <input 
        type="text" 
        className="form-control court-input" 
        placeholder="Court Name" 
        value={court.name}
        onChange={(e) => updateCourtName(court.id, e.target.value)}
        required
      />
    </div>
  );
  
  return (
    <div className="container mt-4">
      <h2>Team & Court Setup</h2>
      
      <form id="teamSetupForm" className="mt-4" onSubmit={handleSubmit}>
        {/* Team Levels Section */}
        <div className="mb-4">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h4>Team Levels</h4>
            <button 
              type="button" 
              className="btn btn-outline-primary btn-sm" 
              onClick={addLevel}
            >
              + Add Level
            </button>
          </div>
          
          <div id="teamLevelsContainer" className="team-levels-container">
            {levels.map(renderLevelColumn)}
          </div>
        </div>
        
        {/* Court Names Section */}
        <div className="court-section">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h4>Court Names</h4>
            <button 
              type="button" 
              className="btn btn-outline-primary btn-sm" 
              onClick={() => addCourt()}
            >
              + Add Court
            </button>
          </div>
          
          <div id="courtsContainer" className="courts-container">
            {courts.map(renderCourtRow)}
          </div>
        </div>
        
        <div className="form-actions mt-4">
          <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>Back to Schedule</button>
          <button type="submit" className="btn btn-success">Continue to Game Assignment</button>
        </div>
      </form>
    </div>
  );
};

export default TeamSetup;