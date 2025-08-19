import React, { useState } from 'react';

const StatsResults = ({ statisticsResults }) => {
  if (!statisticsResults) return null;

  // Fixed scale of 0-10 for all charts
  const getMaxValues = (level) => {
    return { maxPlays: 10, maxRefs: 10, maxTotal: 10 };
  };

  const renderSlotBar = (team, slot, playCount, refCount, maxTotal, slotTime) => {
    const totalCount = playCount + refCount;
    
    // SIMPLE: Total bar height = total count as % of 10
    const totalHeightPercent = (totalCount / 10) * 100; // 8 total = 80%, 10 total = 100%
    
    // Within that total height, split between play and ref proportionally
    const playPortion = totalCount > 0 ? playCount / totalCount : 0; // e.g., 3/8 = 37.5%
    const refPortion = totalCount > 0 ? refCount / totalCount : 0;   // e.g., 5/8 = 62.5%
    
    const playHeight = totalHeightPercent * playPortion;  // 80% * 37.5% = 30%
    const refHeight = totalHeightPercent * refPortion;    // 80% * 62.5% = 50%
    
    
    return (
      <div 
        className="slot-bar" 
        style={{ 
          height: '100px',
          width: '60px',
          position: 'relative',
          border: '1px solid var(--border-primary)',
          borderRadius: '4px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-end',
          backgroundColor: '#f8f9fa',
          margin: '0 2px'
        }}
        title={`${team} at ${slotTime}: ${playCount} games, ${refCount} refs`}
      >
        {/* Referee portion (top) */}
        {refCount > 0 && (
          <div
            style={{
              height: `${refHeight}%`,
              backgroundColor: 'var(--warning)',
              borderRadius: '3px 3px 0 0',
              minHeight: refCount > 0 ? '3px' : '0px',
              position: 'relative'
            }}
          >
            {/* Referee count label */}
            <div 
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: '12px',
                fontWeight: 'bold',
                color: '#fff',
                textShadow: '0 0 3px rgba(0,0,0,0.7)',
                pointerEvents: 'none'
              }}
            >
              {refCount}
            </div>
          </div>
        )}
        
        {/* Play portion (bottom) */}
        {playCount > 0 && (
          <div
            style={{
              height: `${playHeight}%`,
              backgroundColor: 'var(--primary)',
              borderRadius: refCount > 0 ? '0 0 3px 3px' : '3px',
              minHeight: playCount > 0 ? '3px' : '0px',
              position: 'relative'
            }}
          >
            {/* Play count label (in the play section) */}
            <div 
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: '14px',
                fontWeight: 'bold',
                color: '#fff',
                textShadow: '0 0 3px rgba(0,0,0,0.7)',
                pointerEvents: 'none'
              }}
            >
              {playCount}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderLevelStats = (level) => {
    const playData = statisticsResults.team_play_counts[level] || {};
    const refData = statisticsResults.team_ref_counts[level] || {};
    // Use the properly filtered team list from summary to ensure we only show teams from this level
    const teams = (statisticsResults.summary?.team_names_by_level?.[level] || []).sort();
    const slotTimes = statisticsResults.slot_times || {};
    
    if (teams.length === 0) return null;
    
    const { maxTotal } = getMaxValues(level);
    
    // Determine available slots
    const allSlots = new Set();
    Object.values(playData).forEach(teamSlots => {
      Object.keys(teamSlots).forEach(slot => allSlots.add(parseInt(slot)));
    });
    const slots = Array.from(allSlots).sort((a, b) => a - b);
    
    return (
      <div key={level} className="card mb-3">
        <div 
          className="card-header"
          style={{ 
            padding: '0.75rem 1rem', 
            cursor: 'default',
            background: 'linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-muted) 100%)',
            pointerEvents: 'none'
          }}
        >
          <h6 className="mb-0" style={{ pointerEvents: 'none' }}>
            {level} Team Activity
          </h6>
        </div>
        
        <div className="card-content" style={{ padding: '1rem' }}>
          {/* Legend */}
          <div className="d-flex justify-content-center mb-3">
            <div className="d-flex align-items-center me-4">
              <div 
                style={{ 
                  width: '14px', 
                  height: '14px', 
                  backgroundColor: 'var(--primary)',
                  marginRight: '6px',
                  borderRadius: '2px'
                }}
              />
              <small><strong>Total Games</strong></small>
            </div>
            <div className="d-flex align-items-center">
              <div 
                style={{ 
                  width: '14px', 
                  height: '14px', 
                  backgroundColor: 'var(--warning)',
                  marginRight: '6px',
                  borderRadius: '2px'
                }}
              />
              <small><strong>Games Refereed</strong></small>
            </div>
          </div>
          
          {/* Chart - Teams on X-axis, Grouped bars for each time slot */}
          <div>
            <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: '20px' }}>
              
              {/* Y-axis labels */}
              <div style={{ 
                width: '50px', 
                height: '100px', 
                display: 'flex', 
                flexDirection: 'column', 
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '11px',
                color: '#666',
                marginRight: '15px'
              }}>
                <span>10</span>
                <span>7.5</span>
                <span>5</span>
                <span>2.5</span>
                <span>0</span>
              </div>
              
              {/* Team columns */}
              {teams.map(team => (
                <div key={team} style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center',
                  marginRight: '20px'
                }}>
                  
                  {/* Grouped bars for this team */}
                  <div style={{ 
                    display: 'flex',
                    alignItems: 'flex-end',
                    height: '100px',
                    marginBottom: '5px'
                  }}>
                    {slots.map(slot => {
                      const playCount = (playData[team] && playData[team][slot]) || 0;
                      const refCount = (refData[team] && refData[team][slot]) || 0;
                      const slotTime = slotTimes[slot] || `Slot ${slot}`;
                      
                      return (
                        <div key={slot} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          {renderSlotBar(team, slot, playCount, refCount, maxTotal, slotTime)}
                          {/* Time label under each bar */}
                          <div style={{ 
                            fontSize: '9px',
                            color: '#666',
                            textAlign: 'center',
                            marginTop: '3px',
                            width: '60px',
                            lineHeight: '1.1'
                          }}>
                            {slotTime}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  
                  {/* Team name */}
                  <div style={{ 
                    fontSize: '12px',
                    fontWeight: '600',
                    textAlign: 'center',
                    width: `${slots.length * 64}px`,
                    lineHeight: '1.3',
                    marginTop: '5px'
                  }}>
                    {team}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderOverview = () => {
    const { summary, games_per_slot } = statisticsResults;
    const slotTimes = statisticsResults.slot_times || {};
    
    // Calculate total games per time slot
    const slotTotals = {};
    Object.values(games_per_slot).forEach(levelData => {
      Object.entries(levelData).forEach(([slot, count]) => {
        slotTotals[slot] = (slotTotals[slot] || 0) + count;
      });
    });
    
    return (
      <div className="card mb-3">
        <div className="card-content" style={{ padding: '1rem' }}>
          <div className="row align-items-center">
            <div className="col-md-8">
              <div className="d-flex flex-wrap gap-4">
                <div className="d-flex align-items-center">
                  <i className="fas fa-gamepad text-primary me-2"></i>
                  <span><strong>{summary.total_games}</strong> total games</span>
                </div>
                <div className="d-flex align-items-center">
                  <i className="fas fa-layer-group text-info me-2"></i>
                  <span>{summary.levels.length} levels ({summary.levels.join(', ')})</span>
                </div>
                <div className="d-flex align-items-center">
                  <i className="fas fa-users text-success me-2"></i>
                  <span>
                    {Object.entries(summary.teams_per_level).map(([level, count]) => 
                      `${count} × ${level}`
                    ).join(', ')} teams
                  </span>
                </div>
              </div>
            </div>
            <div className="col-md-4">
              <div className="text-end">
                <small className="text-muted">Games per time: </small>
                {Object.entries(slotTotals).map(([slot, total]) => {
                  const slotTime = slotTimes[slot] || `Slot ${slot}`;
                  return (
                    <span key={slot} className="badge bg-secondary ms-1">
                      {slotTime}→{total}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="stats-results-container mb-4">
      <h3 className="mb-3">
        <i className="fas fa-chart-line me-2"></i>
        Schedule Statistics
      </h3>
      
      {renderOverview()}
      
      {/* Level-based team activity charts */}
      {statisticsResults.summary.levels.map(level => renderLevelStats(level))}
    </div>
  );
};

export default StatsResults;