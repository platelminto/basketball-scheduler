import React, { useState } from 'react';
import StandingsTable from './StandingsTable';

const TeamList = ({ 
  teams, 
  onUpdateTeam, 
  onArchiveTeam, 
  onDeleteTeam,
  isArchived = false
}) => {
  const [editingTeam, setEditingTeam] = useState(null);
  const [editName, setEditName] = useState('');
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [expandedTeam, setExpandedTeam] = useState(null);
  const [teamStats, setTeamStats] = useState({});

  const handleStartEdit = (team) => {
    setEditingTeam(team.id);
    setEditName(team.name);
  };

  const handleCancelEdit = () => {
    setEditingTeam(null);
    setEditName('');
  };

  const handleSaveEdit = async (teamId) => {
    if (!editName.trim()) return;
    
    setSaving(true);
    const result = await onUpdateTeam(teamId, editName.trim());
    setSaving(false);
    
    if (result.success) {
      setEditingTeam(null);
      setEditName('');
    } else {
      alert(`Error: ${result.error}`);
    }
  };

  const handleArchiveToggle = async (teamId, currentArchiveStatus) => {
    const action = currentArchiveStatus ? 'unarchive' : 'archive';
    
    setActionLoading(prev => ({ ...prev, [teamId]: action }));
    const result = await onArchiveTeam(teamId, !currentArchiveStatus);
    setActionLoading(prev => ({ ...prev, [teamId]: null }));
    
    if (!result.success) {
      alert(`Error: ${result.error}`);
    }
  };

  const handleDelete = async (teamId) => {
    setActionLoading(prev => ({ ...prev, [teamId]: 'delete' }));
    const result = await onDeleteTeam(teamId);
    setActionLoading(prev => ({ ...prev, [teamId]: null }));
    
    if (!result.success && result.error) {
      alert(`Error: ${result.error}`);
    }
  };

  const handleKeyPress = (e, teamId) => {
    if (e.key === 'Enter') {
      handleSaveEdit(teamId);
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const handleTeamClick = async (team) => {
    if (editingTeam === team.id) return; // Don't expand while editing
    
    if (expandedTeam === team.id) {
      setExpandedTeam(null);
    } else {
      setExpandedTeam(team.id);
      if (!teamStats[team.id]) {
        await fetchTeamStats(team.id);
      }
    }
  };

  const fetchTeamStats = async (teamId) => {
    try {
      const response = await fetch(`/scheduler/api/teams/${teamId}/stats/`);
      if (!response.ok) throw new Error('Failed to fetch team stats');
      
      const data = await response.json();
      setTeamStats(prev => ({ ...prev, [teamId]: data }));
    } catch (err) {
      console.error('Error fetching team stats:', err);
      setTeamStats(prev => ({ ...prev, [teamId]: { error: 'Failed to load stats' } }));
    }
  };

  return (
    <div className="card">
      <div className="card-content">
        {teams && teams.map(team => (
          <div key={team.id}>
            <div 
              title={editingTeam === team.id ? undefined : (expandedTeam === team.id ? null : "Click to show historical standings")}
              style={{ 
                padding: '0.5rem 1rem', 
                borderBottom: expandedTeam === team.id ? 'none' : '1px solid var(--border-primary)', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                cursor: editingTeam === team.id ? 'default' : 'pointer',
                backgroundColor: expandedTeam === team.id ? 'var(--bg-muted)' : 'transparent',
                transition: 'background-color 0.2s ease'
              }}
              onClick={() => handleTeamClick(team)}
              onMouseEnter={(e) => {
                if (editingTeam !== team.id) {
                  e.currentTarget.style.backgroundColor = 'var(--bg-light)';
                }
              }}
              onMouseLeave={(e) => {
                if (editingTeam !== team.id && expandedTeam !== team.id) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {editingTeam === team.id ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
                    <input
                      type="text"
                      className="form-control"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyPress={(e) => handleKeyPress(e, team.id)}
                      autoFocus
                      style={{ flex: 1, maxWidth: '300px' }}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <button 
                      className="btn btn-sm btn-success"
                      onClick={(e) => { e.stopPropagation(); handleSaveEdit(team.id); }}
                      disabled={saving}
                    >
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-secondary"
                      onClick={(e) => { e.stopPropagation(); handleCancelEdit(); }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <span style={{ fontWeight: '500' }}>{team.name}</span>
                    {team.seasons && team.seasons.length > 0 && (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {team.seasons.map(season => (
                          <span 
                            key={season.id}
                            className="badge badge-secondary"
                            style={{ fontSize: '0.7rem' }}
                          >
                            {season.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {editingTeam !== team.id && (
                  <>
                    <button 
                      className="btn btn-sm btn-outline-primary"
                      onClick={(e) => { e.stopPropagation(); handleStartEdit(team); }}
                    >
                      Rename
                    </button>
                    
                    <button 
                      className={`btn btn-sm ${team.is_archived ? 'btn-outline-success' : 'btn-outline-warning'}`}
                      onClick={(e) => { e.stopPropagation(); handleArchiveToggle(team.id, team.is_archived); }}
                      disabled={actionLoading[team.id]}
                    >
                      {actionLoading[team.id] && actionLoading[team.id] !== 'delete' ? 
                        (actionLoading[team.id] === 'archive' ? 'Archiving...' : 'Unarchiving...') :
                        (team.is_archived ? 'Unarchive' : 'Archive')
                      }
                    </button>
                    
                    {team.is_archived && onDeleteTeam && (
                      <button 
                        className="btn btn-sm btn-outline-danger"
                        onClick={(e) => { e.stopPropagation(); handleDelete(team.id); }}
                        disabled={actionLoading[team.id]}
                      >
                        {actionLoading[team.id] === 'delete' ? 'Deleting...' : 'Delete'}
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
            
            {/* Expanded League Tables Section */}
            {expandedTeam === team.id && (
              <div style={{ 
                padding: '1rem', 
                backgroundColor: 'var(--bg-light)', 
                borderBottom: '1px solid var(--border-primary)' 
              }}>
                {teamStats[team.id] ? (
                  teamStats[team.id].error ? (
                    <div style={{ color: 'var(--danger)', fontStyle: 'italic' }}>
                      {teamStats[team.id].error}
                    </div>
                  ) : (
                    <div>
                      <h5 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Season History</h5>
                      {teamStats[team.id].seasons && teamStats[team.id].seasons.length > 0 ? (
                        <div style={{ 
                          display: 'grid', 
                          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                          gap: '1rem' 
                        }}>
                          {teamStats[team.id].seasons.map(season => (
                            <div key={season.season_id} style={{ 
                              padding: '0.75rem', 
                              backgroundColor: 'var(--bg-primary)', 
                              borderRadius: '6px', 
                              border: '1px solid var(--border-primary)' 
                            }}>
                              <h6 style={{ 
                                marginBottom: '0.75rem', 
                                fontSize: '0.9rem', 
                                fontWeight: '600',
                                color: 'var(--text-primary)'
                              }}>
                                {season.season_name}
                              </h6>
                              <StandingsTable 
                                standings={season.standings} 
                                levels={season.levels}
                                showBoth={false}
                                mode="summary"
                              />
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                          No season history available
                        </div>
                      )}
                    </div>
                  )
                ) : (
                  <div style={{ color: 'var(--text-secondary)' }}>Loading stats...</div>
                )}
              </div>
            )}
          </div>
        ))}
        
        {teams.length === 0 && (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            {isArchived ? 'No archived teams found' : 'No active teams found'}
          </div>
        )}
      </div>
    </div>
  );
};

export default TeamList;