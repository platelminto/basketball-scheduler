import { useState, useEffect } from 'react';

export const useStandings = (scheduleData) => {
  const [standings, setStandings] = useState([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (!scheduleData || !scheduleData.season || !scheduleData.season.id) return;
    
    const fetchStandings = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/scheduler/api/seasons/${scheduleData.season.id}/standings/`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Transform backend data to match the expected frontend format
        const transformedStandings = data.standings.map(team => ({
          id: team.team_id,
          name: team.team_name,
          level_id: team.level_id,
          level_name: team.level_name,
          gamesPlayed: team.games_played,
          wins: team.wins,
          losses: team.losses,
          draws: team.draws,
          pointsFor: team.points_for,
          pointsAgainst: team.points_against,
          winPct: team.win_pct,
          pointDiff: team.point_diff,
          headToHead: {} // Head-to-head data not yet implemented in backend
        }));
        
        setStandings(transformedStandings);
      } catch (error) {
        console.error('Error fetching standings:', error);
        setStandings([]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchStandings();
  }, [scheduleData]);
  
  return standings;
};