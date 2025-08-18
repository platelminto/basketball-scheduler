import React, { useState, useEffect, useRef } from 'react';
import TeamList from '../components/TeamList';

const TeamListPage = () => {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showArchived, setShowArchived] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [newTeamName, setNewTeamName] = useState('');
  const [creating, setCreating] = useState(false);
  const newTeamInputRef = useRef(null);

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      setLoading(true);
      const url = `/scheduler/api/teams/?include_archived=true`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      setTeams(data.teams || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching teams:', err);
      setError('Failed to load teams. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async (teamName) => {
    if (!teamName.trim() || creating) return;
    
    try {
      setCreating(true);
      const response = await fetch('/scheduler/api/teams/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ name: teamName.trim() }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to create team');
      }

      // Add new team to the list
      setTeams(prev => [data.team, ...prev]);
      setNewTeamName('');
      
      // Focus the input field after successful creation
      setTimeout(() => {
        if (newTeamInputRef.current) {
          newTeamInputRef.current.focus();
        }
      }, 0);
      
      return { success: true };
    } catch (err) {
      console.error('Error creating team:', err);
      alert(`Error: ${err.message}`);
      return { success: false, error: err.message };
    } finally {
      setCreating(false);
    }
  };

  const handleNewTeamKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleCreateTeam(newTeamName);
    }
  };

  const handleUpdateTeam = async (teamId, newName) => {
    try {
      const response = await fetch(`/scheduler/api/teams/${teamId}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ name: newName }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to update team');
      }

      // Update team in the list
      setTeams(prev => prev.map(team => 
        team.id === teamId ? data.team : team
      ));
      
      return { success: true };
    } catch (err) {
      console.error('Error updating team:', err);
      return { success: false, error: err.message };
    }
  };

  const handleArchiveTeam = async (teamId, archive = true) => {
    try {
      const response = await fetch(`/scheduler/api/teams/${teamId}/archive/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ archive }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to archive team');
      }

      // Update team in the list
      setTeams(prev => prev.map(team => 
        team.id === teamId ? data.team : team
      ));
      
      return { success: true };
    } catch (err) {
      console.error('Error archiving team:', err);
      return { success: false, error: err.message };
    }
  };

  const handleDeleteTeam = async (teamId) => {
    if (!confirm('Are you sure you want to permanently delete this team? This action cannot be undone.')) {
      return { success: false };
    }

    try {
      const response = await fetch(`/scheduler/api/teams/${teamId}/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': getCsrfToken(),
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.message || 'Failed to delete team');
      }

      // Remove team from the list
      setTeams(prev => prev.filter(team => team.id !== teamId));
      
      return { success: true };
    } catch (err) {
      console.error('Error deleting team:', err);
      return { success: false, error: err.message };
    }
  };


  const getCsrfToken = () => {
    return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  };


  const filteredTeams = teams.filter(team =>
    team.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const activeTeams = filteredTeams.filter(team => !team.is_archived);
  const archivedTeams = filteredTeams.filter(team => team.is_archived);

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
          <button className="btn btn-primary" onClick={fetchTeams}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: '2rem' }}>Team Management</h2>

      {/* Search */}
      <input
        type="text"
        className="form-control"
        placeholder="Search teams..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        style={{ marginBottom: '2rem' }}
      />

      {/* Active Teams */}
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '1rem' }}>Active Teams ({activeTeams.length})</h3>
        
        {/* Add New Team Form */}
        <div className="card" style={{ marginBottom: '1rem' }}>
          <div className="card-content">
            <div style={{ 
              padding: '0.5rem 1rem', 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center'
            }}>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  ref={newTeamInputRef}
                  type="text"
                  className="form-control"
                  placeholder="Enter new team name..."
                  value={newTeamName}
                  onChange={(e) => setNewTeamName(e.target.value)}
                  onKeyPress={handleNewTeamKeyPress}
                  disabled={creating}
                  style={{ flex: 1, maxWidth: '300px' }}
                />
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button 
                  className="btn btn-sm btn-success"
                  onClick={() => handleCreateTeam(newTeamName)}
                  disabled={creating || !newTeamName.trim()}
                >
                  {creating ? 'Adding...' : 'Add Team'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Active Teams List */}
        {activeTeams.length > 0 ? (
          <TeamList
            teams={activeTeams}
            onUpdateTeam={handleUpdateTeam}
            onArchiveTeam={handleArchiveTeam}
            isArchived={false}
          />
        ) : (
          <div className="alert alert-info" style={{ textAlign: 'center', padding: '2rem' }}>
            No active teams found
          </div>
        )}
      </div>

      {/* Archived Teams - Collapsible */}
      {archivedTeams.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <button 
            className="btn btn-outline-secondary"
            onClick={() => setShowArchived(!showArchived)}
            style={{ marginBottom: '1rem' }}
          >
            {showArchived ? 'Hide' : 'Show'} Archived Teams ({archivedTeams.length})
          </button>
          {showArchived && (
            <TeamList
              teams={archivedTeams}
              onUpdateTeam={handleUpdateTeam}
              onArchiveTeam={handleArchiveTeam}
              onDeleteTeam={handleDeleteTeam}
              isArchived={true}
            />
          )}
        </div>
      )}

      {/* No teams message */}
      {filteredTeams.length === 0 && (
        <div className="alert alert-info" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <h4>No teams found</h4>
          <p>
            {searchTerm 
              ? `No teams match "${searchTerm}". Try adjusting your search.`
              : 'Create your first team to get started.'
            }
          </p>
        </div>
      )}


    </div>
  );
};

export default TeamListPage;