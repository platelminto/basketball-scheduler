import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_TEAMS_DATA } from '../contexts/ScheduleContext';

const OrganizationCreate = () => {
  const { dispatch } = useSchedule();
  const navigate = useNavigate();
  const [availableTeams, setAvailableTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Default levels and courts - start with 6 team slots per level
  const [levels, setLevels] = useState(() => {
    const defaultLevels = [
      { id: Date.now() + 1, name: 'Mid', teams: [] },
      { id: Date.now() + 2, name: 'High', teams: [] },
      { id: Date.now() + 3, name: 'Top', teams: [] }
    ];
    
    // Add 6 empty team slots to each level
    return defaultLevels.map(level => ({
      ...level,
      teams: Array.from({ length: 6 }, (_, i) => ({
        id: Date.now() + Math.random() + i,
        name: '',
        sourceId: null
      }))
    }));
  });
  const [courts, setCourts] = useState([
    { id: Date.now() + 4, name: 'Court 1' },
    { id: Date.now() + 5, name: 'Court 2' },
    { id: Date.now() + 6, name: 'Court 3' }
  ]);
  const [slotDuration, setSlotDuration] = useState(70);

  useEffect(() => {
    fetchAllActiveTeams();
  }, []);

  const fetchAllActiveTeams = async () => {
    try {
      setLoading(true);
      const response = await fetch('/scheduler/api/teams/?include_archived=false');
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      setAvailableTeams(data.teams || []);
      setError('');
    } catch (err) {
      console.error('Error fetching teams:', err);
      setError('Failed to load teams. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
  const addTeam = (levelId) => {
    setLevels(levels.map(level => {
      if (level.id === levelId) {
        return {
          ...level,
          teams: [
            ...level.teams,
            {
              id: Date.now() + Math.random(),
              name: ''
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
  
  const updateTeamSelection = (levelId, teamId, selectedTeamId) => {
    setLevels(levels.map(level => {
      if (level.id === levelId) {
        return {
          ...level,
          teams: level.teams.map(team => {
            if (team.id === teamId) {
              const selectedTeam = availableTeams.find(t => t.id === parseInt(selectedTeamId));
              return { 
                ...team, 
                name: selectedTeam ? selectedTeam.name : '',
                sourceId: selectedTeam ? selectedTeam.id : null
              };
            }
            return team;
          })
        };
      }
      return level;
    }));
  };

  // Court management functions
  const addCourt = () => {
    const nextCourtNum = courts.length + 1;
    setCourts([
      ...courts,
      {
        id: Date.now() + Math.random(),
        name: `Court ${nextCourtNum}`
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
    
    // Convert levels to the format expected by the parent
    const levelsData = [];
    levels.forEach(level => {
      if (level.name.trim()) {
        const teamsArray = level.teams
          .filter(team => team.name.trim() !== '')
          .map(team => ({
            id: team.sourceId || team.id,
            name: team.name.trim()
          }));
          
        levelsData.push({
          id: level.id,
          name: level.name.trim(),
          teams: teamsArray
        });
      }
    });
    
    // Convert courts to array of strings
    const courtNames = courts
      .map(court => court.name.trim())
      .filter(name => name !== '');

    // Check for empty team assignments
    let hasEmptyLevels = false;
    levelsData.forEach(level => {
      if (level.teams.length === 0) {
        hasEmptyLevels = true;
      }
    });

    if (hasEmptyLevels) {
      if (!confirm("Some levels don't have any teams. Continue anyway?")) {
        return;
      }
    }
    
    // Build the setup data
    const setupData = {
      levels: levelsData,
      courts: courtNames,
      slot_duration_minutes: slotDuration,
      teams: levelsData.reduce((acc, level) => {
        acc[level.name] = level.teams.map(team => ({
          id: team.sourceId || team.id,
          name: team.name
        }));
        return acc;
      }, {})
    };
    
    dispatch({ type: SET_TEAMS_DATA, payload: setupData });
    navigate('/seasons/create/schedule', { state: { setupData } });
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-container">
          <div className="spinner"></div>
          <span>Loading teams...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert alert-danger">
          <h4>Error loading teams</h4>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchAllActiveTeams}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Get used team IDs to prevent duplicates
  const getUsedTeamIds = () => {
    const usedIds = new Set();
    levels.forEach(level => {
      level.teams.forEach(team => {
        if (team.sourceId) {
          usedIds.add(team.sourceId);
        }
      });
    });
    return usedIds;
  };

  const usedTeamIds = getUsedTeamIds();

  return (
    <div className="page-container">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h2>Step 1: Team Setup</h2>
          <p style={{ color: 'var(--text-secondary)' }}>
            Select existing teams from dropdowns and assign them to levels for this season.
          </p>
        </div>
        <a
          href="/scheduler/app/teams"
          className="btn btn-success"
        >
          Manage Teams
        </a>
      </div>
      
      <form onSubmit={handleSubmit}>
        {/* Team Levels Section */}
        <div className="mb-4">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h4>Team Levels</h4>
            <button 
              type="button" 
              className="btn btn-outline-primary btn-sm" 
              onClick={addLevel}
            >
              + Add Level
            </button>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
            {levels.map(level => (
              <div key={level.id} className="card">
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input 
                      type="text" 
                      className="form-control" 
                      value={level.name} 
                      onChange={(e) => updateLevelName(level.id, e.target.value)}
                      required
                      style={{ fontWeight: '500' }}
                    />
                    <button 
                      type="button" 
                      className="btn btn-outline-danger btn-sm"
                      onClick={() => deleteLevel(level.id)}
                      style={{ flexShrink: 0 }}
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="card-content">
                  <div style={{ display: 'grid', gap: '0.75rem' }}>
                    {level.teams.map(team => (
                      <div key={team.id} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <button 
                          type="button" 
                          className="btn btn-outline-danger btn-sm"
                          onClick={() => deleteTeam(level.id, team.id)}
                          style={{ flexShrink: 0, width: '2rem', height: '2rem' }}
                        >
                          ×
                        </button>
                        <select
                          className="form-select"
                          value={team.sourceId || ''}
                          onChange={(e) => updateTeamSelection(level.id, team.id, e.target.value)}
                          required
                        >
                          <option value="">Select a team...</option>
                          {availableTeams
                            .filter(availableTeam => !usedTeamIds.has(availableTeam.id) || availableTeam.id === team.sourceId)
                            .map(availableTeam => (
                              <option key={availableTeam.id} value={availableTeam.id}>
                                {availableTeam.name}
                              </option>
                            ))}
                        </select>
                      </div>
                    ))}
                  </div>
                  <button 
                    type="button" 
                    className="btn btn-outline-secondary btn-sm mt-3"
                    onClick={() => addTeam(level.id)}
                    style={{ width: '100%' }}
                  >
                    + Add Team
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Court Names Section */}
        <div className="mb-4">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h4>Court Names</h4>
            <button 
              type="button" 
              className="btn btn-outline-primary btn-sm" 
              onClick={addCourt}
            >
              + Add Court
            </button>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
            {courts.map(court => (
              <div key={court.id} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button 
                  type="button" 
                  className="btn btn-outline-danger btn-sm"
                  onClick={() => deleteCourt(court.id)}
                  style={{ flexShrink: 0, width: '2rem', height: '2rem' }}
                >
                  ×
                </button>
                <input 
                  type="text" 
                  className="form-control" 
                  placeholder="Court Name" 
                  value={court.name}
                  onChange={(e) => updateCourtName(court.id, e.target.value)}
                  required
                />
              </div>
            ))}
          </div>
        </div>
        
        {/* Game Slot Duration Section */}
        <div className="mb-4">
          <h4 style={{ marginBottom: '1rem' }}>Game Duration</h4>
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
        
        {/* Actions */}
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', paddingTop: '2rem', borderTop: '1px solid var(--border-primary)' }}>
          <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>
            <i className="fas fa-arrow-left"></i> Back to Seasons
          </button>
          <button type="submit" className="btn btn-primary">
            Continue to Game Assignment <i className="fas fa-arrow-right"></i>
          </button>
        </div>
      </form>
    </div>
  );
};

export default OrganizationCreate;