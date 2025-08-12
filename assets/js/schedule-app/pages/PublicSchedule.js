import React, { useState, useEffect } from 'react';

const PublicSchedule = () => {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLevel, setSelectedLevel] = useState('all');

  // Fetch public schedule data
  useEffect(() => {
    const fetchScheduleData = async () => {
      try {
        const response = await fetch('/scheduler/api/public/schedule/');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setScheduleData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchScheduleData();
  }, []);

  if (loading) {
    return (
      <div className="container mt-4">
        <div className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2">Loading schedule...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mt-4">
        <div className="alert alert-danger">
          <h4>Error loading schedule</h4>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!scheduleData) {
    return (
      <div className="container mt-4">
        <div className="alert alert-warning">
          <h4>No schedule data available</h4>
          <p>There may be no active season or no games scheduled.</p>
        </div>
      </div>
    );
  }

  // Filter games by selected level
  const filterGamesByLevel = (games) => {
    if (selectedLevel === 'all') return games;
    return games.filter(game => game.level_id === parseInt(selectedLevel));
  };

  // Get day name from day_of_week number
  const getDayName = (dayOfWeek) => {
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    return days[dayOfWeek] || '';
  };

  // Format date for display
  const formatDate = (mondayDate, dayOfWeek) => {
    if (dayOfWeek === null || dayOfWeek === undefined) return '';
    
    const date = new Date(mondayDate);
    date.setDate(date.getDate() + dayOfWeek);
    return date.toLocaleDateString('en-GB', { 
      day: '2-digit', 
      month: '2-digit' 
    });
  };

  // Format week header with day info
  const formatWeekHeader = (week) => {
    const mondayDate = new Date(week.monday_date);
    const dayName = mondayDate.toLocaleDateString('en-GB', { weekday: 'long' });
    const dateStr = mondayDate.toLocaleDateString('en-GB', { 
      day: 'numeric', 
      month: 'long' 
    });
    return `${dayName}, ${dateStr}`;
  };

  // Check if all games in week are on same day
  const areAllGamesSameDay = (games) => {
    if (games.length === 0) return false;
    const firstDay = games[0].day_of_week;
    return games.every(game => game.day_of_week === firstDay);
  };

  // Check if game is completed (has both scores)
  const isGameCompleted = (game) => {
    return game.team1_score !== null && game.team1_score !== '' &&
           game.team2_score !== null && game.team2_score !== '';
  };

  // Get winner info for styling
  const getWinnerInfo = (game) => {
    if (!isGameCompleted(game)) return { team1Wins: false, team2Wins: false, tie: false };
    
    const score1 = parseInt(game.team1_score);
    const score2 = parseInt(game.team2_score);
    
    if (score1 > score2) return { team1Wins: true, team2Wins: false, tie: false };
    if (score2 > score1) return { team1Wins: false, team2Wins: true, tie: false };
    return { team1Wins: false, team2Wins: false, tie: true };
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px' }}>
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '600', marginBottom: '15px' }}>
          {scheduleData.season.name}
        </h1>
        
        {/* Level Filter */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setSelectedLevel('all')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '4px',
              background: selectedLevel === 'all' ? '#333' : '#f5f5f5',
              color: selectedLevel === 'all' ? 'white' : '#333',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            All Levels
          </button>
          {scheduleData.levels.map(level => (
            <button
              key={level.id}
              onClick={() => setSelectedLevel(level.id.toString())}
              style={{
                padding: '8px 16px',
                border: 'none',
                borderRadius: '4px',
                background: selectedLevel === level.id.toString() ? '#333' : '#f5f5f5',
                color: selectedLevel === level.id.toString() ? 'white' : '#333',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              {level.name}
            </button>
          ))}
        </div>
      </div>

      {/* Schedule Display */}
      <div>
        {(() => {
          const sortedWeeks = Object.values(scheduleData.weeks).sort((a, b) => a.week_number - b.week_number);
          let gameWeekCounter = 0;
          
          return sortedWeeks.map(week => {
            if (week.isOffWeek) {
              return (
                <div key={`week-${week.week_number}`} style={{ marginBottom: '35px' }}>
                  <div style={{ 
                    background: '#f8f9fa',
                    border: '1px solid #e9ecef',
                    borderRadius: '6px',
                    padding: '20px',
                    textAlign: 'center'
                  }}>
                    <h3 style={{ fontSize: '16px', fontWeight: '600', margin: '0 0 8px 0' }}>
                      {new Date(week.monday_date).toLocaleDateString('en-GB', { 
                        weekday: 'long', 
                        day: 'numeric', 
                        month: 'long' 
                      })}
                    </h3>
                    <p style={{ color: '#6c757d', margin: '0', fontSize: '14px' }}>
                      Off Week - No games scheduled
                    </p>
                  </div>
                </div>
              );
            }

            const filteredGames = filterGamesByLevel(week.games);
            if (filteredGames.length === 0) return null;

            // Increment the game week counter for display
            gameWeekCounter++;

            return (
              <div key={`week-${week.week_number}`} style={{ marginBottom: '40px' }}>
                <div style={{ 
                  background: '#f8f9fa',
                  border: '1px solid #e9ecef',
                  borderRadius: '6px',
                  padding: '12px 18px',
                  marginBottom: '20px'
                }}>
                  <h3 style={{ fontSize: '18px', fontWeight: '600', margin: '0', color: '#333' }}>
                    Week {gameWeekCounter} - {formatWeekHeader(week)}
                  </h3>
                </div>
                
                <div style={{ paddingLeft: '20px' }}>
                  {/* Show day info if not all games are on same day */}
                  {!areAllGamesSameDay(filteredGames) && filteredGames.length > 1 && (
                    <div style={{ marginBottom: '10px', fontSize: '13px', color: '#666' }}>
                      Multiple days this week
                    </div>
                  )}
                  
                  {filteredGames.map(game => {
                    const winnerInfo = getWinnerInfo(game);
                    
                    return (
                    <div 
                      key={game.id} 
                      style={{ 
                        display: 'grid',
                        gridTemplateColumns: 'auto 1fr auto 1fr auto',
                        alignItems: 'center',
                        padding: '10px 0',
                        borderBottom: '1px solid #eee',
                        gap: '15px'
                      }}
                    >
                      {/* Left - Time info */}
                      <div style={{ color: '#666', minWidth: '70px' }}>
                        {game.time && <div style={{ fontSize: '15px', fontWeight: '500' }}>{game.time}</div>}
                        {!areAllGamesSameDay(filteredGames) && game.day_of_week !== null && (
                          <div style={{ fontSize: '11px' }}>
                            {getDayName(game.day_of_week)}
                          </div>
                        )}
                        {game.court && (
                          <div style={{ fontSize: '11px' }}>
                            {game.court}
                          </div>
                        )}
                      </div>
                      
                      {/* Team 1 */}
                      <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                        {isGameCompleted(game) && winnerInfo.team1Wins && (
                          <span style={{ marginRight: '6px', fontSize: '12px', color: '#333' }}>▸</span>
                        )}
                        <div style={{ 
                          fontSize: '15px', 
                          fontWeight: '500',
                          color: isGameCompleted(game)
                            ? (winnerInfo.team1Wins || winnerInfo.tie ? '#333' : '#666')
                            : '#333'
                        }}>
                          {game.team1_name}
                        </div>
                      </div>
                      
                      {/* Center - Score/VS and Referee */}
                      <div style={{ textAlign: 'center', minWidth: '60px' }}>
                        {isGameCompleted(game) ? (
                          <div style={{ fontSize: '16px', fontWeight: '600' }}>
                            {game.team1_score} - {game.team2_score}
                          </div>
                        ) : (
                          <div style={{ fontSize: '14px', color: '#999' }}>
                            vs
                          </div>
                        )}
                        {/* Referee info */}
                        {(game.referee_name || game.referee_team_id) && (
                          <div style={{ fontSize: '11px', color: '#888', marginTop: '2px' }}>
                            Ref: {game.referee_name || 
                              Object.values(scheduleData.teams_by_level)
                                .flat()
                                .find(team => team.id === game.referee_team_id)?.name || 
                              'TBD'
                            }
                          </div>
                        )}
                      </div>
                      
                      {/* Team 2 */}
                      <div style={{ textAlign: 'left', display: 'flex', alignItems: 'center', justifyContent: 'flex-start' }}>
                        <div style={{ 
                          fontSize: '15px', 
                          fontWeight: '500',
                          color: isGameCompleted(game)
                            ? (winnerInfo.team2Wins || winnerInfo.tie ? '#333' : '#666')
                            : '#333'
                        }}>
                          {game.team2_name}
                        </div>
                        {isGameCompleted(game) && winnerInfo.team2Wins && (
                          <span style={{ marginLeft: '6px', fontSize: '12px', color: '#333' }}>◂</span>
                        )}
                      </div>
                      
                      {/* Right - Level */}
                      <div style={{ textAlign: 'right', minWidth: '50px' }}>
                        <span style={{ 
                          background: '#f0f0f0', 
                          padding: '3px 8px', 
                          borderRadius: '3px',
                          fontSize: '12px',
                          fontWeight: '600'
                        }}>
                          {game.level_name}
                        </span>
                      </div>
                    </div>
                    );
                  })}
                </div>
              </div>
            );
          });
        })()}
      </div>
    </div>
  );
};

export default PublicSchedule;