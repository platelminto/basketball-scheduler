import React from 'react';

const StandingsTable = ({ standings, levels, showBoth, mode = "full" }) => {
  const isSummary = mode === "summary";
  
  if (!standings || standings.length === 0) {
    return (
      <div style={{ 
        padding: '20px', 
        background: '#f8f9fa', 
        border: '1px solid #ddd', 
        borderRadius: '6px',
        textAlign: 'center',
        color: '#666'
      }}>
        No teams found for standings.
      </div>
    );
  }

  return (
    <div style={{ 
      position: showBoth ? 'sticky' : 'static', 
      top: showBoth ? '20px' : 'auto',
      marginBottom: !showBoth ? '30px' : '0'
    }}>
      
      <div style={{ 
        display: isSummary ? 'flex' : 'block',
        gap: isSummary ? '20px' : '0',
        flexWrap: 'wrap',
        justifyContent: isSummary ? 'space-evenly' : 'normal'
      }}>
        {levels.sort((a, b) => a.id - b.id).map(level => {
        const levelStandings = standings.filter(team => team.level_id === level.id);
        if (levelStandings.length === 0) return null;
      
        return (
          <div key={level.id} style={{ marginBottom: '25px' }}>
            <h3 style={{ 
              fontSize: '16px', 
              fontWeight: '600', 
              marginBottom: '8px',
              color: '#333',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              {level.name}
            </h3>
            
            <div style={{
              border: '1px solid #ddd',
              borderRadius: '6px',
              overflow: 'auto',
              fontSize: '12px',
              maxWidth: isSummary ? 'fit-content' : showBoth ? 'none' : '600px',
              minWidth: isSummary ? 'auto' : '320px'
            }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: isSummary 
                  ? '25px 140px 25px 20px 20px 20px 30px'
                  : showBoth ? '30px 150px 30px 25px 25px 25px 50px 35px 35px 35px' : '30px minmax(160px, 1fr) 30px 25px 25px 25px 50px 35px 35px 35px',
                background: '#f8f9fa',
                padding: '8px 6px',
                fontWeight: '600',
                borderBottom: '1px solid #ddd',
                gap: '4px'
              }}>
                <div style={{ textAlign: 'center' }}>#</div>
                <div>Team</div>
                <div style={{ textAlign: 'center' }}>GP</div>
                <div style={{ textAlign: 'center' }}>W</div>
                <div style={{ textAlign: 'center' }}>L</div>
                <div style={{ textAlign: 'center' }}>D</div>
                {!isSummary && <div style={{ textAlign: 'center' }}>PCT</div>}
                {!isSummary && <div style={{ textAlign: 'center' }}>PF</div>}
                {!isSummary && <div style={{ textAlign: 'center' }}>PA</div>}
                <div style={{ textAlign: 'center' }}>PD</div>
              </div>
              
              {levelStandings.map((team, index) => (
                <div key={team.id} style={{
                  display: 'grid',
                  gridTemplateColumns: isSummary 
                    ? '25px 140px 25px 20px 20px 20px 30px'
                    : showBoth ? '30px 150px 30px 25px 25px 25px 50px 35px 35px 35px' : '30px minmax(160px, 1fr) 30px 25px 25px 25px 50px 35px 35px 35px',
                  padding: '6px 6px',
                  borderBottom: index < levelStandings.length - 1 ? '1px solid #eee' : 'none',
                  backgroundColor: index % 2 === 0 ? 'white' : '#fafafa',
                  gap: '4px',
                  alignItems: 'center'
                }}>
                  <div style={{ textAlign: 'center', fontWeight: '600', color: '#666' }}>
                    {index + 1}
                  </div>
                  <div style={{ 
                    fontSize: '13px', 
                    fontWeight: '400',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {team.name}
                  </div>
                  <div style={{ textAlign: 'center' }}>{team.gamesPlayed}</div>
                  <div style={{ textAlign: 'center' }}>{team.wins}</div>
                  <div style={{ textAlign: 'center' }}>{team.losses}</div>
                  <div style={{ textAlign: 'center' }}>{team.draws}</div>
                  {!isSummary && (
                    <div style={{ textAlign: 'center' }}>
                      {team.gamesPlayed > 0 ? team.winPct.toFixed(3) : '0.000'}
                    </div>
                  )}
                  {!isSummary && <div style={{ textAlign: 'center' }}>{team.pointsFor}</div>}
                  {!isSummary && <div style={{ textAlign: 'center' }}>{team.pointsAgainst}</div>}
                  <div style={{ 
                    textAlign: 'center',
                    color: team.pointDiff > 0 ? '#28a745' : team.pointDiff < 0 ? '#dc3545' : '#666',
                    fontWeight: team.pointDiff !== 0 ? '500' : 'normal'
                  }}>
                    {team.pointDiff > 0 ? '+' : ''}{team.pointDiff}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
        })}
      </div>
    </div>
  );
};

export default StandingsTable;