import React from 'react';
import { filterGames } from '../utils/filterUtils';
import { getGameWeekNumbers } from '../utils/weekUtils';
import { 
  formatWeekHeader, 
  areAllGamesSameDay, 
  getDayName, 
  isGameCompleted, 
  getWinnerInfo,
  hasUnusualTimes 
} from '../utils/gameUtils';

const ScheduleDisplay = ({ scheduleData, filters, commonWeekTimes }) => {
  const [screenWidth, setScreenWidth] = React.useState(typeof window !== 'undefined' ? window.innerWidth : 1200);
  
  React.useEffect(() => {
    const handleResize = () => setScreenWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  const isMobile = screenWidth < 768;
  const sortedWeeks = Object.values(scheduleData.weeks).sort((a, b) => a.week_number - b.week_number);
  
  const weekNumbers = getGameWeekNumbers(scheduleData.weeks);
  
  return (
    <div>
      {filters.hidePastGames && !isMobile && (
        <div style={{
          background: '#e3f2fd',
          border: '1px solid #bbdefb',
          borderRadius: '6px',
          padding: '12px 16px',
          marginBottom: '20px',
          fontSize: '14px',
          color: '#1565c0',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span>ℹ️</span>
          <span>Showing upcoming games only (past games hidden)</span>
        </div>
      )}
      {sortedWeeks.map(week => {
        if (week.isOffWeek) {
          return (
            <div key={`week-${week.week_number}`} style={{ marginBottom: '35px' }}>
              <div style={{ 
                background: '#f1f5f9',
                border: '2px solid #64748b',
                borderRadius: '4px',
                padding: '20px',
                display: 'grid',
                gridTemplateColumns: '120px 1fr 120px',
                alignItems: 'center',
                gap: '20px',
                boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
              }}>
                <div style={{ fontSize: '14px', color: '#4b5563' }}>
                  {new Date(week.monday_date).toLocaleDateString('en-US', { 
                    weekday: 'long', 
                    month: 'long', 
                    day: 'numeric'
                  })}
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '20px', fontWeight: '700', color: '#1f2937', marginBottom: '4px', letterSpacing: '0.5px' }}>
                    <strong>OFF WEEK</strong>
                  </div>
                  <div style={{ fontSize: '15px', color: '#4b5563' }}>
                    No games scheduled
                  </div>
                </div>
                <div></div>
              </div>
            </div>
          );
        }

        const filteredGames = filterGames(week.games, week.monday_date, filters, scheduleData);
        if (filteredGames.length === 0) return null;

        const weekHasUnusualTimes = hasUnusualTimes(week, commonWeekTimes);
        
        return (
          <div key={`week-${week.week_number}`} style={{ marginBottom: '40px' }}>
            <div style={{ 
              background: '#e5e7eb',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              padding: '12px 18px',
              marginBottom: '20px'
            }}>
              <h3 style={{ fontSize: '18px', fontWeight: '600', margin: '0', color: '#1f2937' }}>
                Week {weekNumbers[week.week_number]} - {formatWeekHeader(week)}
              </h3>
              
              {weekHasUnusualTimes && (
                <div style={{
                  background: '#fff3cd',
                  border: '1px solid #ffeaa7',
                  borderRadius: '4px',
                  padding: '6px 10px',
                  marginTop: '8px',
                  fontSize: '13px',
                  color: '#856404',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <span>⚠️</span>
                  <span>This week has different game times than usual</span>
                </div>
              )}
            </div>
            
            <div style={{ paddingLeft: '20px' }}>
              {!areAllGamesSameDay(filteredGames) && filteredGames.length > 1 && (
                <div style={{ marginBottom: '10px', fontSize: '13px', color: '#444' }}>
                  Multiple days this week
                </div>
              )}
              
              {filteredGames.map((game, index) => {
                const winnerInfo = getWinnerInfo(game);
                const nextGame = filteredGames[index + 1];
                const hasTimeChange = nextGame && game.time !== nextGame.time;
                const isFirstGame = index === 0;
                const isLastGame = index === filteredGames.length - 1;
                
                if (isMobile) {
                  return (
                    <div 
                      key={game.id} 
                      style={{ 
                        padding: '12px 0',
                        borderTop: isFirstGame ? '1px solid #ddd' : 'none',
                        borderBottom: (hasTimeChange || isLastGame) ? '1px solid #ddd' : '1px solid #eee'
                      }}
                    >
                      {/* Top row: Time/Day/Court and Level */}
                      <div style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        marginBottom: '8px'
                      }}>
                        <div style={{ color: '#333' }}>
                          {game.time && <span style={{ fontSize: '14px', fontWeight: '500' }}>{game.time}</span>}
                          {!areAllGamesSameDay(filteredGames) && game.day_of_week !== null && (
                            <span style={{ fontSize: '12px', marginLeft: '8px' }}>
                              {getDayName(game.day_of_week)}
                            </span>
                          )}
                          {game.court && (
                            <span style={{ fontSize: '12px', marginLeft: '8px' }}>
                              {game.court}
                            </span>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {(game.referee_name || game.referee_team_id) && (
                            <span style={{ 
                              fontSize: '11px', 
                              color: '#555'
                            }}>
                              Ref: {game.referee_name || 
                                Object.values(scheduleData.teams_by_level)
                                  .flat()
                                  .find(team => team.id === game.referee_team_id)?.name || 
                                'TBD'
                              }
                            </span>
                          )}
                          <span style={{ 
                            background: '#f0f0f0', 
                            padding: '3px 8px', 
                            borderRadius: '3px',
                            fontSize: '11px',
                            fontWeight: '600'
                          }}>
                            {game.level_name}
                          </span>
                        </div>
                      </div>
                      
                      {/* Main matchup row */}
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        gap: '12px',
                        marginBottom: '4px'
                      }}>
                        <div style={{ 
                          flex: 1, 
                          textAlign: 'right',
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'flex-end' 
                        }}>
                          {isGameCompleted(game) && (winnerInfo.team1Wins || winnerInfo.tie) && (
                            <span style={{ marginRight: '6px', fontSize: '12px', color: '#333' }}>▸</span>
                          )}
                          <div style={{ 
                            fontSize: '14px', 
                            fontWeight: '500',
                            color: isGameCompleted(game)
                              ? (winnerInfo.team1Wins || winnerInfo.tie ? '#333' : '#666')
                              : '#333'
                          }}>
                            {game.team1_name}
                          </div>
                        </div>
                        
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
                        </div>
                        
                        <div style={{ 
                          flex: 1, 
                          textAlign: 'left',
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'flex-start' 
                        }}>
                          <div style={{ 
                            fontSize: '14px', 
                            fontWeight: '500',
                            color: isGameCompleted(game)
                              ? (winnerInfo.team2Wins || winnerInfo.tie ? '#333' : '#666')
                              : '#333'
                          }}>
                            {game.team2_name}
                          </div>
                          {isGameCompleted(game) && (winnerInfo.team2Wins || winnerInfo.tie) && (
                            <span style={{ marginLeft: '6px', fontSize: '12px', color: '#333' }}>◂</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                } else {
                  // Desktop layout
                  return (
                    <div 
                      key={game.id} 
                      style={{ 
                        display: 'grid',
                        gridTemplateColumns: 'auto 1fr auto 1fr auto',
                        alignItems: 'center',
                        padding: '10px 0',
                        borderTop: isFirstGame ? '1px solid #ddd' : 'none',
                        borderBottom: (hasTimeChange || isLastGame) ? '1px solid #ddd' : '1px solid #eee',
                        gap: '15px'
                      }}
                    >
                      <div style={{ color: '#333', minWidth: '70px' }}>
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
                      
                      <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                        {isGameCompleted(game) && (winnerInfo.team1Wins || winnerInfo.tie) && (
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
                        {(game.referee_name || game.referee_team_id) && (
                          <div style={{ fontSize: '11px', color: '#555', marginTop: '2px' }}>
                            Ref: {game.referee_name || 
                              Object.values(scheduleData.teams_by_level)
                                .flat()
                                .find(team => team.id === game.referee_team_id)?.name || 
                              'TBD'
                            }
                          </div>
                        )}
                      </div>
                      
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
                        {isGameCompleted(game) && (winnerInfo.team2Wins || winnerInfo.tie) && (
                          <span style={{ marginLeft: '6px', fontSize: '12px', color: '#333' }}>◂</span>
                        )}
                      </div>
                      
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
                }
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ScheduleDisplay;