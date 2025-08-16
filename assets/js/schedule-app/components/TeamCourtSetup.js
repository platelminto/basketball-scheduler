import React, { useState, useEffect } from 'react';

const TeamCourtSetup = ({ 
  initialLevels = null, 
  initialCourts = null, 
  onSubmit, 
  onCancel, 
  submitButtonText = "Continue", 
  cancelButtonText = "Cancel",
  showCancelButton = true,
  editMode = false
}) => {
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
  
  const [levels, setLevels] = useState(initialLevels || defaultLevels);
  const [courts, setCourts] = useState(initialCourts || defaultCourts);
  const [slotDuration, setSlotDuration] = useState(70);
  
  // Generate default teams for each level if not provided
  useEffect(() => {
    if (!initialLevels) {
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
    }
  }, [initialLevels]);
  
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
    
    // Convert levels to the format expected by the parent, including IDs for tracking renames
    const levelsData = [];
    levels.forEach(level => {
      if (level.name.trim()) {
        const teamsArray = level.teams
          .map(team => ({
            id: team.id,
            name: team.name.trim()
          }))
          .filter(team => team.name !== '');
          
        levelsData.push({
          id: level.id,
          name: level.name.trim(),
          teams: teamsArray
        });
      }
    });
    
    // Convert courts to array of objects with names and IDs
    const courtNames = courts
      .map(court => court.name.trim())
      .filter(name => name !== '');

    // Check for empty team names
    let hasEmptyTeams = false;
    levelsData.forEach(level => {
      if (level.teams.length === 0) {
        hasEmptyTeams = true;
      }
    });

    if (hasEmptyTeams) {
      if (!confirm("Some levels don't have any teams. Continue anyway?")) {
        return;
      }
    }
    
    // Build the setup data with both old and new formats for backward compatibility
    const setupData = {
      // New format with IDs for rename tracking
      levels: levelsData,
      courts: courtNames,
      slot_duration_minutes: slotDuration,
      // Old format for backward compatibility
      teams: levelsData.reduce((acc, level) => {
        acc[level.name] = level.teams.map(team => team.name);
        return acc;
      }, {})
    };
    
    onSubmit(setupData);
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
        {!editMode && (
          <button 
            type="button" 
            className="btn btn-outline-danger btn-delete-small"
            onClick={() => deleteLevel(level.id)}
          >
            ×
          </button>
        )}
      </div>
      <div className="teams-container">
        {level.teams.map(team => renderTeamRow(level.id, team))}
      </div>
      {!editMode && (
        <button 
          type="button" 
          className="btn btn-outline-secondary btn-sm mt-2 add-team-btn"
          onClick={() => addTeam(level.id)}
        >
          + Add Team
        </button>
      )}
    </div>
  );
  
  const renderTeamRow = (levelId, team) => (
    <div className="team-row" key={team.id}>
      {!editMode && (
        <button 
          type="button" 
          className="btn btn-outline-danger btn-delete-small"
          onClick={() => deleteTeam(levelId, team.id)}
        >
          ×
        </button>
      )}
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
      {!editMode && (
        <button 
          type="button" 
          className="btn btn-outline-danger btn-delete-small"
          onClick={() => deleteCourt(court.id)}
        >
          ×
        </button>
      )}
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
    <form id="teamSetupForm" className="mt-4" onSubmit={handleSubmit}>
      {/* Team Levels Section */}
      <div className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h4>Team Levels</h4>
          {!editMode && (
            <button 
              type="button" 
              className="btn btn-outline-primary btn-sm" 
              onClick={addLevel}
            >
              + Add Level
            </button>
          )}
        </div>
        
        <div id="teamLevelsContainer" className="team-levels-container">
          {levels.map(renderLevelColumn)}
        </div>
      </div>
      
      {/* Court Names Section */}
      <div className="court-section">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h4>Court Names</h4>
          {!editMode && (
            <button 
              type="button" 
              className="btn btn-outline-primary btn-sm" 
              onClick={() => addCourt()}
            >
              + Add Court
            </button>
          )}
        </div>
        
        <div id="courtsContainer" className="courts-container">
          {courts.map(renderCourtRow)}
        </div>
      </div>
      
      {/* Game Slot Duration Section */}
      <div className="slot-duration-section mb-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h4>Game Duration</h4>
        </div>
        <div className="form-section">
          <label className="form-label" htmlFor="slotDuration">
            Game Slot Duration (minutes)
            <span style={{ color: 'var(--text-secondary)', fontSize: '13px', fontWeight: 'normal', marginLeft: '8px' }}>
              Includes game time + halftime + time between games
            </span>
          </label>
          <input
            id="slotDuration"
            type="number"
            className="form-control"
            style={{ maxWidth: '200px' }}
            value={slotDuration}
            onChange={(e) => setSlotDuration(parseInt(e.target.value) || 70)}
            min="30"
            max="180"
            required
          />
        </div>
      </div>
      
      <div className="form-actions mt-4">
        {showCancelButton && (
          <button 
            type="button" 
            className="btn btn-secondary" 
            onClick={onCancel}
          >
            {cancelButtonText}
          </button>
        )}
        <button type="submit" className="btn btn-success">{submitButtonText}</button>
      </div>
    </form>
  );
};

export default TeamCourtSetup;