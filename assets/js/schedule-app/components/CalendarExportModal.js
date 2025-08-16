import React, { useState } from 'react';

const CalendarExportModal = ({ scheduleData, onClose }) => {
  const [step, setStep] = useState('select'); // 'select' or 'export'
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [includeReffing, setIncludeReffing] = useState(true);
  const [includeTournaments, setIncludeTournaments] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);
  const [copyStatus, setCopyStatus] = useState(''); // 'copied', 'error', or ''

  if (!scheduleData) return null;

  // Debug: log the scheduleData structure
  console.log('CalendarExportModal scheduleData:', scheduleData);

  // Get all teams organized by level
  const teamsByLevel = scheduleData.levels.map(level => ({
    ...level,
    teams: scheduleData.teams_by_level[level.id] || []
  })).filter(level => level.teams.length > 0);

  console.log('teamsByLevel:', teamsByLevel);

  const generateCalendarUrl = (teamId) => {
    const baseUrl = `/scheduler/api/teams/${teamId}/calendar.ics`;
    const params = new URLSearchParams();
    
    if (includeReffing) params.append('include_reffing', 'true');
    params.append('include_scores', 'true'); // Always include scores
    if (includeTournaments) params.append('include_tournaments', 'true');
    
    const queryString = params.toString();
    return queryString ? `${baseUrl}?${queryString}` : baseUrl;
  };

  const handleDownload = (teamId) => {
    const url = generateCalendarUrl(teamId);
    window.location.href = url;
  };

  const copySubscriptionUrl = (teamId) => {
    const url = window.location.origin + generateCalendarUrl(teamId);
    navigator.clipboard.writeText(url).then(() => {
      setCopyStatus('copied');
      setTimeout(() => setCopyStatus(''), 2000);
    }).catch(() => {
      setCopyStatus('error');
      setTimeout(() => setCopyStatus(''), 3000);
    });
  };

  const selectTeam = (team) => {
    setSelectedTeam(team);
    setStep('export');
  };

  const goBack = () => {
    setStep('select');
    setSelectedTeam(null);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        maxWidth: '600px',
        width: '100%',
        maxHeight: '80vh',
        overflow: 'auto',
        position: 'relative',
        padding: '20px'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {step === 'export' && (
              <button
                onClick={goBack}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '16px',
                  cursor: 'pointer',
                  color: 'var(--text-secondary)'
                }}
              >
                ←
              </button>
            )}
            <h3 style={{ margin: 0, fontSize: '18px' }}>
              📅 {step === 'select' ? 'Select Team' : `Calendar for ${selectedTeam?.name}`}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#666'
            }}
          >
            ×
          </button>
        </div>

        <div>
          {step === 'select' ? (
            /* Team Selection Step */
            <div>
              {teamsByLevel.length === 0 ? (
                <p>No teams found.</p>
              ) : (
                teamsByLevel.map(level => (
                  <div key={level.id} style={{ marginBottom: '20px' }}>
                    <h4 style={{ 
                      fontSize: '14px', 
                      fontWeight: '600', 
                      marginBottom: '10px',
                      color: 'var(--text-secondary)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}>
                      {level.name}
                    </h4>
                    
                    <div style={{ 
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '1px' 
                    }}>
                      {level.teams.map(team => (
                        <button
                          key={team.id}
                          onClick={() => selectTeam(team)}
                          style={{
                            padding: '8px 16px',
                            border: 'none',
                            borderRadius: '0',
                            backgroundColor: 'transparent',
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: '400',
                            transition: 'all 0.15s ease',
                            borderBottom: '1px solid #f0f0f0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                          }}
                          onMouseEnter={(e) => {
                            e.target.style.backgroundColor = '#3b82f6';
                            e.target.style.color = 'white';
                            e.target.querySelector('.arrow').style.opacity = '1';
                          }}
                          onMouseLeave={(e) => {
                            e.target.style.backgroundColor = 'transparent';
                            e.target.style.color = 'inherit';
                            e.target.querySelector('.arrow').style.opacity = '0.3';
                          }}
                        >
                          <span>{team.name}</span>
                          <span className="arrow" style={{ opacity: '0.3', transition: 'opacity 0.15s ease' }}>→</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            /* Export Options Step */
            <div>
              {/* Options */}
              <div style={{ marginBottom: '30px' }}>
                <h4 style={{ fontSize: '15px', marginBottom: '16px', color: '#374151', fontWeight: '500' }}>Options</h4>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    fontSize: '14px',
                    color: '#4b5563'
                  }}>
                    <input
                      type="checkbox"
                      checked={includeReffing}
                      onChange={(e) => setIncludeReffing(e.target.checked)}
                      style={{ marginRight: '10px', transform: 'scale(1.1)' }}
                    />
                    Include games where team is refereeing
                  </label>
                  
                  <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    fontSize: '14px',
                    color: '#4b5563'
                  }}>
                    <input
                      type="checkbox"
                      checked={includeTournaments}
                      onChange={(e) => setIncludeTournaments(e.target.checked)}
                      style={{ marginRight: '10px', transform: 'scale(1.1)' }}
                    />
                    Include tournaments
                  </label>
                </div>
              </div>

              {/* Export Actions */}
              <div style={{ marginBottom: '30px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <button
                    onClick={() => copySubscriptionUrl(selectedTeam.id)}
                    style={{
                      padding: '14px 20px',
                      border: copyStatus === 'copied' ? '1px solid #10b981' : '1px solid #e5e7eb',
                      borderRadius: '6px',
                      backgroundColor: copyStatus === 'copied' ? '#f0fdf4' : '#ffffff',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: '500',
                      color: '#374151',
                      transition: 'all 0.15s ease',
                      textAlign: 'left'
                    }}
                    onMouseEnter={(e) => {
                      if (copyStatus !== 'copied') {
                        e.target.style.borderColor = '#3b82f6';
                        e.target.style.backgroundColor = '#f8fafc';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (copyStatus !== 'copied') {
                        e.target.style.borderColor = '#e5e7eb';
                        e.target.style.backgroundColor = '#ffffff';
                      }
                    }}
                  >
                    <div>
                      <div style={{ marginBottom: '2px' }}>
                        {copyStatus === 'copied' ? '✅ URL copied to clipboard!' : 
                         copyStatus === 'error' ? '❌ Failed to copy' :
                         '🔗 Copy subscription URL (recommended)'}
                      </div>
                      <div style={{ fontSize: '12px', color: '#6b7280' }}>
                        Auto-updates when schedule changes
                      </div>
                    </div>
                  </button>
                  
                  <button
                    onClick={() => handleDownload(selectedTeam.id)}
                    style={{
                      padding: '14px 20px',
                      border: '1px solid #e5e7eb',
                      borderRadius: '6px',
                      backgroundColor: '#ffffff',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: '500',
                      color: '#374151',
                      transition: 'all 0.15s ease',
                      textAlign: 'left'
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.borderColor = '#3b82f6';
                      e.target.style.backgroundColor = '#f8fafc';
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.borderColor = '#e5e7eb';
                      e.target.style.backgroundColor = '#ffffff';
                    }}
                  >
                    <div>
                      <div style={{ marginBottom: '2px' }}>📥 Download .ics file</div>
                      <div style={{ fontSize: '12px', color: '#6b7280' }}>One-time import to your calendar</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Instructions */}
              <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: '20px' }}>
                <h4 style={{ fontSize: '15px', marginBottom: '15px', color: '#374151', fontWeight: '500' }}>How to add to your calendar</h4>
                
                <div style={{ 
                  fontSize: '13px',
                  lineHeight: '1.5',
                  color: '#4b5563'
                }}>
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontWeight: '600', marginBottom: '6px' }}>📱 iPhone/iPad:</div>
                    <div>After copying the URL, open Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar. Paste the URL.</div>
                  </div>
                  
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontWeight: '600', marginBottom: '6px' }}>🖥️ Mac:</div>
                    <div>Open Calendar app → File → New Calendar Subscription. Paste the URL.</div>
                  </div>
                  
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontWeight: '600', marginBottom: '6px' }}>📧 Google Calendar:</div>
                    <div>Go to calendar.google.com → Settings → Add Calendar → From URL. Paste the URL.</div>
                  </div>
                  
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontWeight: '600', marginBottom: '6px' }}>🏢 Outlook:</div>
                    <div>Right-click "Other calendars" → Add calendar → Subscribe from web. Paste the URL.</div>
                  </div>
                  
                  <div style={{ 
                    padding: '12px', 
                    backgroundColor: '#f0f9ff', 
                    borderRadius: '4px',
                    border: '1px solid #e0f2fe',
                    marginTop: '12px'
                  }}>
                    <strong>💡 Pro tip:</strong> Your calendar will automatically refresh every few hours to show any schedule changes.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CalendarExportModal;