import { useMemo } from 'react';
import { isGameCompleted } from '../utils/gameUtils';

export const useStandings = (scheduleData) => {
  return useMemo(() => {
    if (!scheduleData) return [];
    
    const teamStats = {};
    const headToHead = {};
    
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
    
    const teamNameToId = {};
    Object.keys(scheduleData.teams_by_level).forEach(levelId => {
      const levelTeams = scheduleData.teams_by_level[levelId];
      levelTeams.forEach(team => {
        teamNameToId[team.name] = team.id;
      });
    });
    
    Object.values(scheduleData.weeks).forEach(week => {
      if (!week.isOffWeek) {
        week.games.forEach(game => {
          if (isGameCompleted(game)) {
            const team1Id = teamNameToId[game.team1_name];
            const team2Id = teamNameToId[game.team2_name];
              
            if (team1Id && team2Id && teamStats[team1Id] && teamStats[team2Id]) {
              const score1 = parseInt(game.team1_score);
              const score2 = parseInt(game.team2_score);
              
              teamStats[team1Id].gamesPlayed++;
              teamStats[team2Id].gamesPlayed++;
              
              teamStats[team1Id].pointsFor += score1;
              teamStats[team1Id].pointsAgainst += score2;
              teamStats[team2Id].pointsFor += score2;
              teamStats[team2Id].pointsAgainst += score1;
              
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
    
    standings.sort((a, b) => {
      if (a.level_id !== b.level_id) return a.level_id - b.level_id;
      
      if (Math.abs(a.winPct - b.winPct) > 0.001) {
        return b.winPct - a.winPct;
      }
      
      if (a.pointDiff !== b.pointDiff) {
        return b.pointDiff - a.pointDiff;
      }
      
      if (a.pointsAgainst !== b.pointsAgainst) {
        return a.pointsAgainst - b.pointsAgainst;
      }
      
      const h2h = a.headToHead[b.id];
      if (h2h && (h2h.wins + h2h.losses + h2h.draws) > 0) {
        if (h2h.wins !== h2h.losses) {
          return h2h.losses - h2h.wins;
        }
        return h2h.pointDiff;
      }
      
      return 0;
    });
    
    return standings;
  }, [scheduleData]);
};