import React, { useState, useEffect } from 'react';

const MultiSelectDropdown = ({ options, selectedValues, onChange, placeholder, allLabel = "All" }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('[data-dropdown]')) {
        setIsOpen(false);
      }
    };
    
    if (isOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isOpen]);
  
  const handleOptionClick = (optionValue) => {
    if (optionValue === 'all') {
      onChange(['all']);
    } else {
      const newValues = selectedValues.includes('all') 
        ? [optionValue]
        : selectedValues.includes(optionValue)
          ? selectedValues.filter(val => val !== optionValue)
          : [...selectedValues.filter(val => val !== 'all'), optionValue];
      
      onChange(newValues.length === 0 ? ['all'] : newValues);
    }
  };

  const getDisplayText = () => {
    if (selectedValues.includes('all') || selectedValues.length === 0) {
      return allLabel;
    }
    if (selectedValues.length === 1) {
      const option = options.find(opt => opt.value === selectedValues[0]);
      return option ? option.label : selectedValues[0];
    }
    return `${selectedValues.length} selected`;
  };

  return (
    <div data-dropdown style={{ position: 'relative', minWidth: '140px' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '8px 12px',
          border: '1px solid #ddd',
          borderRadius: '4px',
          background: 'white',
          cursor: 'pointer',
          fontSize: '14px',
          width: '100%',
          textAlign: 'left',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span>{getDisplayText()}</span>
        <span style={{ marginLeft: '8px' }}>▼</span>
      </button>
      
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          background: 'white',
          border: '1px solid #ddd',
          borderTop: 'none',
          borderRadius: '0 0 4px 4px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          zIndex: 1000,
          maxHeight: '200px',
          overflowY: 'auto'
        }}>
          <div
            onClick={() => handleOptionClick('all')}
            style={{
              padding: '8px 12px',
              cursor: 'pointer',
              backgroundColor: selectedValues.includes('all') ? '#f0f0f0' : 'transparent',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <input
              type="checkbox"
              checked={selectedValues.includes('all')}
              readOnly
              style={{ marginRight: '8px' }}
            />
            {allLabel}
          </div>
          {options.map(option => (
            <div
              key={option.value}
              onClick={() => handleOptionClick(option.value)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                backgroundColor: selectedValues.includes(option.value) ? '#f0f0f0' : 'transparent',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <input
                type="checkbox"
                checked={selectedValues.includes(option.value)}
                readOnly
                style={{ marginRight: '8px' }}
              />
              {option.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const PublicSchedule = () => {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLevels, setSelectedLevels] = useState(['all']);
  const [selectedCourts, setSelectedCourts] = useState(['all']);
  const [selectedReferees, setSelectedReferees] = useState(['all']);
  const [selectedTeams, setSelectedTeams] = useState(['all']);
  const [hidePastGames, setHidePastGames] = useState(false);
  const [viewMode, setViewMode] = useState('both'); // 'both', 'standings', 'schedule'
  const [screenWidth, setScreenWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1400);

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

  // Handle window resize for responsive layout
  useEffect(() => {
    const handleResize = () => setScreenWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
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

  // Check if a game is in the past
  const isGameInPast = (game, weekMondayDate) => {
    if (!game.time || game.day_of_week === null || game.day_of_week === undefined) {
      return false; // Can't determine if past, so show it
    }
    
    const gameDate = new Date(weekMondayDate);
    gameDate.setDate(gameDate.getDate() + game.day_of_week);
    
    // Parse time (format: "HH:MM" or "H:MM")
    const [hours, minutes] = game.time.split(':').map(num => parseInt(num, 10));
    gameDate.setHours(hours, minutes, 0, 0);
    
    return gameDate < new Date();
  };

  // Filter games by all selected filters
  const filterGames = (games, weekMondayDate) => {
    return games.filter(game => {
      // Level filter
      const levelMatch = selectedLevels.includes('all') || selectedLevels.includes(game.level_id.toString());
      
      // Court filter
      const courtMatch = selectedCourts.includes('all') || selectedCourts.includes(game.court || 'No Court');
      
      // Referee filter
      const refereeValue = game.referee_name || 
        (game.referee_team_id ? 
          Object.values(scheduleData.teams_by_level)
            .flat()
            .find(team => team.id === game.referee_team_id)?.name || 'TBD'
          : 'TBD');
      const refereeMatch = selectedReferees.includes('all') || selectedReferees.includes(refereeValue);
      
      // Team filter
      const teamMatch = selectedTeams.includes('all') || 
        selectedTeams.includes(game.team1_name) || 
        selectedTeams.includes(game.team2_name);
      
      // Past games filter
      const timeMatch = !hidePastGames || !isGameInPast(game, weekMondayDate);
      
      return levelMatch && courtMatch && refereeMatch && teamMatch && timeMatch;
    });
  };

  // Calculate standings for all teams
  const calculateStandings = () => {
    if (!scheduleData) return [];
    
    const teamStats = {};
    const headToHead = {};
    
    // Initialize all teams
    Object.keys(scheduleData.teams_by_level).forEach(levelId => {
      const levelTeams = scheduleData.teams_by_level[levelId];
      levelTeams.forEach(team => {
        teamStats[team.id] = {
          id: team.id,
          name: team.name,
          level_id: parseInt(levelId),
          level_name: scheduleData.levels.find(l => l.id === parseInt(levelId))?.name || '',
          gamesPlayed: 0,
          wins: 0,
          losses: 0,
          draws: 0,
          pointsFor: 0,
          pointsAgainst: 0
        };
        headToHead[team.id] = {};
      });
    });
    
    // Create a team name to ID lookup for faster matching
    const teamNameToId = {};
    Object.keys(scheduleData.teams_by_level).forEach(levelId => {
      const levelTeams = scheduleData.teams_by_level[levelId];
      levelTeams.forEach(team => {
        teamNameToId[team.name] = team.id;
      });
    });
    
    // Process all completed games
    Object.values(scheduleData.weeks).forEach(week => {
      if (!week.isOffWeek) {
        week.games.forEach(game => {
          if (isGameCompleted(game)) {
            const team1Id = teamNameToId[game.team1_name];
            const team2Id = teamNameToId[game.team2_name];
              
            if (team1Id && team2Id && teamStats[team1Id] && teamStats[team2Id]) {
              const score1 = parseInt(game.team1_score);
              const score2 = parseInt(game.team2_score);
              
              // Update games played
              teamStats[team1Id].gamesPlayed++;
              teamStats[team2Id].gamesPlayed++;
              
              // Update points
              teamStats[team1Id].pointsFor += score1;
              teamStats[team1Id].pointsAgainst += score2;
              teamStats[team2Id].pointsFor += score2;
              teamStats[team2Id].pointsAgainst += score1;
              
              // Update wins/losses/draws
              if (score1 > score2) {
                teamStats[team1Id].wins++;
                teamStats[team2Id].losses++;
              } else if (score2 > score1) {
                teamStats[team2Id].wins++;
                teamStats[team1Id].losses++;
              } else {
                teamStats[team1Id].draws++;
                teamStats[team2Id].draws++;
              }
              
              // Track head-to-head
              if (!headToHead[team1Id][team2Id]) {
                headToHead[team1Id][team2Id] = { wins: 0, losses: 0, draws: 0, pointDiff: 0 };
              }
              if (!headToHead[team2Id][team1Id]) {
                headToHead[team2Id][team1Id] = { wins: 0, losses: 0, draws: 0, pointDiff: 0 };
              }
              
              if (score1 > score2) {
                headToHead[team1Id][team2Id].wins++;
                headToHead[team2Id][team1Id].losses++;
              } else if (score2 > score1) {
                headToHead[team2Id][team1Id].wins++;
                headToHead[team1Id][team2Id].losses++;
              } else {
                headToHead[team1Id][team2Id].draws++;
                headToHead[team2Id][team1Id].draws++;
              }
              
              headToHead[team1Id][team2Id].pointDiff += (score1 - score2);
              headToHead[team2Id][team1Id].pointDiff += (score2 - score1);
            }
          }
        });
      }
    });
    
    // Calculate derived stats and create final array
    const standings = Object.values(teamStats).map(team => {
      const totalGames = team.gamesPlayed;
      const winPct = totalGames > 0 ? team.wins / totalGames : 0;
      const pointDiff = team.pointsFor - team.pointsAgainst;
      
      return {
        ...team,
        winPct,
        pointDiff,
        headToHead: headToHead[team.id] || {}
      };
    });
    
    // Sort by: PCT desc > PD desc > PA asc > H2H
    standings.sort((a, b) => {
      // Filter to same level for comparison
      if (a.level_id !== b.level_id) return a.level_id - b.level_id;
      
      // 1. Win percentage (higher is better)
      if (Math.abs(a.winPct - b.winPct) > 0.001) {
        return b.winPct - a.winPct;
      }
      
      // 2. Point differential (higher is better)
      if (a.pointDiff !== b.pointDiff) {
        return b.pointDiff - a.pointDiff;
      }
      
      // 3. Points against (lower is better)
      if (a.pointsAgainst !== b.pointsAgainst) {
        return a.pointsAgainst - b.pointsAgainst;
      }
      
      // 4. Head-to-head (if they played each other)
      const h2h = a.headToHead[b.id];
      if (h2h && (h2h.wins + h2h.losses + h2h.draws) > 0) {
        if (h2h.wins !== h2h.losses) {
          return h2h.losses - h2h.wins; // More wins against opponent is better
        }
        return h2h.pointDiff; // Better point differential in head-to-head
      }
      
      return 0; // Equal
    });
    
    return standings;
  };

  // Get unique values for filter options
  const getFilterOptions = () => {
    if (!scheduleData) return { courts: [], referees: [], teams: [] };
    
    const courts = new Set();
    const referees = new Set();
    const teams = new Set();
    
    Object.values(scheduleData.weeks).forEach(week => {
      if (!week.isOffWeek) {
        week.games.forEach(game => {
          if (game.court) courts.add(game.court);
          else courts.add('No Court');
          
          const refereeValue = game.referee_name || 
            (game.referee_team_id ? 
              Object.values(scheduleData.teams_by_level)
                .flat()
                .find(team => team.id === game.referee_team_id)?.name || 'TBD'
              : 'TBD');
          referees.add(refereeValue);
          
          teams.add(game.team1_name);
          teams.add(game.team2_name);
        });
      }
    });
    
    return {
      courts: Array.from(courts).sort(),
      referees: Array.from(referees).sort(),
      teams: Array.from(teams).sort()
    };
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
    const dayName = mondayDate.toLocaleDateString('en-US', { weekday: 'long' });
    const dateStr = mondayDate.toLocaleDateString('en-US', { 
      month: 'long',
      day: 'numeric'
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

  const filterOptions = getFilterOptions();
  const standings = calculateStandings();
  
  // Get most common week time pattern to identify unusual weeks
  const getMostCommonWeekPattern = () => {
    if (!scheduleData) return [];
    
    const weekPatternCounts = {};
    
    Object.values(scheduleData.weeks).forEach(week => {
      if (!week.isOffWeek && week.games.length > 0) {
        // Create a pattern signature for this week (sorted unique times)
        const weekTimes = [...new Set(week.games
          .map(game => game.time)
          .filter(time => time))]
          .sort();
        
        const pattern = weekTimes.join(',');
        weekPatternCounts[pattern] = (weekPatternCounts[pattern] || 0) + 1;
      }
    });
    
    // Find the most common week pattern
    const mostCommonPattern = Object.entries(weekPatternCounts)
      .sort(([,a], [,b]) => b - a)[0];
    
    return mostCommonPattern ? mostCommonPattern[0].split(',') : [];
  };
  
  const commonWeekTimes = getMostCommonWeekPattern();
  
  console.log('Most common week pattern:', commonWeekTimes);
  
  // Check if a week has unusual game times compared to the most common week pattern
  const hasUnusualTimes = (week) => {
    if (week.isOffWeek || commonWeekTimes.length === 0) return false;
    
    const weekTimes = [...new Set(week.games
      .map(game => game.time)
      .filter(time => time))]
      .sort();
    
    // Compare this week's times to the most common week pattern
    const isDifferent = weekTimes.length !== commonWeekTimes.length || 
      weekTimes.some(time => !commonWeekTimes.includes(time));
    
    return isDifferent;
  };
  
  // Check if we have enough space for both (simple viewport-based approach)
  const canShowBoth = screenWidth >= 1200;
  const showBoth = canShowBoth && viewMode === 'both';
  const showStandingsOnly = viewMode === 'standings' || (!canShowBoth && viewMode === 'both');
  const showScheduleOnly = viewMode === 'schedule' || (!showStandingsOnly && !showBoth);

  return (
    <div style={{ maxWidth: showBoth ? '1600px' : '1000px', margin: '0 auto', padding: '20px' }}>
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '600', marginBottom: '15px' }}>
          {scheduleData.season.name}
        </h1>
        
        {/* Filter Controls */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', 
          gap: '15px',
          marginBottom: '15px',
          maxWidth: '600px'
        }}>
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
              Levels
            </label>
            <MultiSelectDropdown
              options={scheduleData.levels.map(level => ({ value: level.id.toString(), label: level.name }))}
              selectedValues={selectedLevels}
              onChange={setSelectedLevels}
              allLabel="All Levels"
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
              Courts
            </label>
            <MultiSelectDropdown
              options={filterOptions.courts.map(court => ({ value: court, label: court }))}
              selectedValues={selectedCourts}
              onChange={setSelectedCourts}
              allLabel="All Courts"
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
              Referees
            </label>
            <MultiSelectDropdown
              options={filterOptions.referees.map(ref => ({ value: ref, label: ref }))}
              selectedValues={selectedReferees}
              onChange={setSelectedReferees}
              allLabel="All Referees"
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
              Teams
            </label>
            <MultiSelectDropdown
              options={filterOptions.teams.map(team => ({ value: team, label: team }))}
              selectedValues={selectedTeams}
              onChange={setSelectedTeams}
              allLabel="All Teams"
            />
          </div>
        </div>
        
        {/* Additional Controls */}
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => setHidePastGames(!hidePastGames)}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '4px',
              background: hidePastGames ? '#333' : '#f5f5f5',
              color: hidePastGames ? 'white' : '#333',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
          >
            {hidePastGames ? '✓ Hide Past Games' : 'Hide Past Games'}
          </button>
          
          {/* View Toggle - only show if we can't fit both or user wants to toggle */}
          {(!canShowBoth || viewMode !== 'both') && (
            <div style={{ display: 'flex', gap: '5px' }}>
              <button
                onClick={() => setViewMode(canShowBoth ? 'both' : 'standings')}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  background: showStandingsOnly ? '#333' : '#f5f5f5',
                  color: showStandingsOnly ? 'white' : '#333',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                Standings
              </button>
              <button
                onClick={() => setViewMode('schedule')}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  background: showScheduleOnly ? '#333' : '#f5f5f5',
                  color: showScheduleOnly ? 'white' : '#333',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                Schedule
              </button>
              {canShowBoth && (
                <button
                  onClick={() => setViewMode('both')}
                  style={{
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '4px',
                    background: showBoth ? '#333' : '#f5f5f5',
                    color: showBoth ? 'white' : '#333',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: '500'
                  }}
                >
                  Both
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Content: Standings and Schedule */}
      <div style={{ 
        display: showBoth ? 'grid' : 'block',
        gridTemplateColumns: showBoth ? '500px 1fr' : 'none',
        gap: showBoth ? '30px' : '0',
        alignItems: 'start'
      }}>
        {/* Standings Table */}
        {(showBoth || showStandingsOnly) && (
        <div style={{ 
          position: showBoth ? 'sticky' : 'static', 
          top: showBoth ? '20px' : 'auto',
          marginBottom: showStandingsOnly ? '30px' : '0'
        }}>
          <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '15px' }}>
            League Standings
          </h2>
          
          {standings.length === 0 ? (
            <div style={{ 
              padding: '20px', 
              background: '#f8f9fa', 
              border: '1px solid #ddd', 
              borderRadius: '6px',
              textAlign: 'center',
              color: '#666'
            }}>
              No standings data available yet.
              <br />
              <small>Games need to be completed to calculate standings.</small>
            </div>
          ) : (
            scheduleData.levels.sort((a, b) => b.id - a.id).map(level => {
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
                  overflow: 'hidden',
                  fontSize: '12px'
                }}>
                  {/* Header */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '30px 150px 30px 25px 25px 25px 50px 35px 35px 35px',
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
                    <div style={{ textAlign: 'center' }}>PCT</div>
                    <div style={{ textAlign: 'center' }}>PF</div>
                    <div style={{ textAlign: 'center' }}>PA</div>
                    <div style={{ textAlign: 'center' }}>PD</div>
                  </div>
                  
                  {/* Rows */}
                  {levelStandings.map((team, index) => (
                    <div key={team.id} style={{
                      display: 'grid',
                      gridTemplateColumns: '30px 150px 30px 25px 25px 25px 50px 35px 35px 35px',
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
                      <div style={{ textAlign: 'center' }}>
                        {team.gamesPlayed > 0 ? team.winPct.toFixed(3) : '0.000'}
                      </div>
                      <div style={{ textAlign: 'center' }}>{team.pointsFor}</div>
                      <div style={{ textAlign: 'center' }}>{team.pointsAgainst}</div>
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
          })
          )}
        </div>
        )}

        {/* Schedule Display */}
        {(showBoth || showScheduleOnly) && (
        <div>
        {(() => {
          const sortedWeeks = Object.values(scheduleData.weeks).sort((a, b) => a.week_number - b.week_number);
          
          // Pre-calculate week numbers for game weeks (unaffected by filtering)
          const weekNumbers = {};
          let gameWeekCounter = 0;
          sortedWeeks.forEach(week => {
            if (!week.isOffWeek) {
              gameWeekCounter++;
              weekNumbers[week.week_number] = gameWeekCounter;
            }
          });
          
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
                      {new Date(week.monday_date).toLocaleDateString('en-US', { 
                        weekday: 'long'
                      })}, {new Date(week.monday_date).toLocaleDateString('en-US', { 
                        month: 'long', 
                        day: 'numeric'
                      })}
                    </h3>
                    <p style={{ color: '#6c757d', margin: '0', fontSize: '14px' }}>
                      Off Week - No games scheduled
                    </p>
                  </div>
                </div>
              );
            }

            const filteredGames = filterGames(week.games, week.monday_date);
            if (filteredGames.length === 0) return null;

            const weekHasUnusualTimes = hasUnusualTimes(week);
            
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
                        {isGameCompleted(game) && (winnerInfo.team2Wins || winnerInfo.tie) && (
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
        )}
      </div>
    </div>
  );
};

export default PublicSchedule;