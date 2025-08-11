import { useState } from 'react';
import { SET_SCHEDULE_DATA } from '../contexts/ScheduleContext';

/**
 * Custom hook for managing random fill functionality
 * @param {Object} state - Schedule context state
 * @param {Function} dispatch - Schedule context dispatch function
 * @returns {Object} Random fill state and functions
 */
export const useRandomFill = (state, dispatch) => {
  const [isRandomFilling, setIsRandomFilling] = useState(false);

  /**
   * Randomly assigns teams and referees to empty games
   */
  const randomFillSchedule = () => {
    setIsRandomFilling(true);
    
    try {
      // Make a deep copy of the current weeks
      const updatedWeeks = JSON.parse(JSON.stringify(state.weeks));
      
      // For each level, create arrays of teams
      const teamsByLevelArray = {};
      
      for (const levelId in state.teamsByLevel) {
        if (state.teamsByLevel[levelId] && state.teamsByLevel[levelId].length > 0) {
          teamsByLevelArray[levelId] = [...state.teamsByLevel[levelId]];
        }
      }
      
      // Process each week
      for (const weekId in updatedWeeks) {
        const week = updatedWeeks[weekId];
        
        // Skip off weeks
        if (week.isOffWeek) continue;
        
        // Group games by level
        const gamesByLevel = {};
        
        // Initialize tracking for teams that already have games this week
        const teamsWithGamesThisWeek = {};
        const teamsWithRefDutyThisWeek = {};
        
        // First pass - identify existing assignments
        week.games.forEach(game => {
          if (game.isDeleted) return;
          
          // Skip games that already have assignments
          if (game.level_id && game.team1_id && game.team2_id) {
            // Track teams that already have games this week
            if (!teamsWithGamesThisWeek[game.level_id]) {
              teamsWithGamesThisWeek[game.level_id] = new Set();
            }
            if (game.team1_id) teamsWithGamesThisWeek[game.level_id].add(game.team1_id);
            if (game.team2_id) teamsWithGamesThisWeek[game.level_id].add(game.team2_id);
            
            // Track teams that already have referee duty this week
            if (game.referee_team_id) {
              if (!teamsWithRefDutyThisWeek[game.level_id]) {
                teamsWithRefDutyThisWeek[game.level_id] = new Set();
              }
              teamsWithRefDutyThisWeek[game.level_id].add(game.referee_team_id);
            }
          }
          
          // Group games by level
          if (game.level_id) {
            if (!gamesByLevel[game.level_id]) {
              gamesByLevel[game.level_id] = [];
            }
            gamesByLevel[game.level_id].push(game);
          }
        });
        
        // Second pass - assign random teams to empty games
        week.games.forEach(game => {
          if (game.isDeleted) return;
          
          // If the game has no level assigned, randomly assign one
          if (!game.level_id) {
            const availableLevels = state.levels.filter(level => 
              teamsByLevelArray[level.id] && teamsByLevelArray[level.id].length >= 2
            );
            
            if (availableLevels.length > 0) {
              const randomLevel = availableLevels[Math.floor(Math.random() * availableLevels.length)];
              game.level_id = randomLevel.id;
              game.level_name = randomLevel.name;
              
              // Initialize tracking for this level if needed
              if (!teamsWithGamesThisWeek[game.level_id]) {
                teamsWithGamesThisWeek[game.level_id] = new Set();
              }
              if (!teamsWithRefDutyThisWeek[game.level_id]) {
                teamsWithRefDutyThisWeek[game.level_id] = new Set();
              }
              if (!gamesByLevel[game.level_id]) {
                gamesByLevel[game.level_id] = [];
              }
              gamesByLevel[game.level_id].push(game);
            }
          }
          
          // Skip if we don't have a level or there are no teams in this level
          if (!game.level_id || !teamsByLevelArray[game.level_id]) return;
          
          // If team1 is not assigned, assign a random team
          if (!game.team1_id) {
            // Filter out teams that already have a game this week if possible
            let availableTeams = teamsByLevelArray[game.level_id].filter(team => 
              !teamsWithGamesThisWeek[game.level_id]?.has(team.id)
            );
            
            // If no available teams, use all teams
            if (availableTeams.length < 1) {
              availableTeams = teamsByLevelArray[game.level_id];
            }
            
            if (availableTeams.length > 0) {
              const randomIndex = Math.floor(Math.random() * availableTeams.length);
              const team = availableTeams[randomIndex];
              
              game.team1_id = team.id;
              game.team1_name = team.name;
              
              // Mark this team as having a game this week
              teamsWithGamesThisWeek[game.level_id].add(team.id);
            }
          }
          
          // If team2 is not assigned, assign a random team (different from team1)
          if (!game.team2_id && game.team1_id) {
            // Filter out team1 and teams that already have a game this week if possible
            let availableTeams = teamsByLevelArray[game.level_id].filter(team => 
              team.id !== game.team1_id && 
              !teamsWithGamesThisWeek[game.level_id]?.has(team.id)
            );
            
            // If no available teams, use all teams except team1
            if (availableTeams.length < 1) {
              availableTeams = teamsByLevelArray[game.level_id].filter(team => 
                team.id !== game.team1_id
              );
            }
            
            if (availableTeams.length > 0) {
              const randomIndex = Math.floor(Math.random() * availableTeams.length);
              const team = availableTeams[randomIndex];
              
              game.team2_id = team.id;
              game.team2_name = team.name;
              
              // Mark this team as having a game this week
              teamsWithGamesThisWeek[game.level_id].add(team.id);
            }
          }
          
          // If referee is not assigned, assign a random team (different from team1 and team2)
          if (!game.referee_team_id && !game.referee_name && game.team1_id && game.team2_id) {
            // Filter out team1, team2, and teams that already have ref duty this week if possible
            let availableTeams = teamsByLevelArray[game.level_id].filter(team => 
              team.id !== game.team1_id && 
              team.id !== game.team2_id && 
              !teamsWithRefDutyThisWeek[game.level_id]?.has(team.id)
            );
            
            // If no available teams, use all teams except team1 and team2
            if (availableTeams.length < 1) {
              availableTeams = teamsByLevelArray[game.level_id].filter(team => 
                team.id !== game.team1_id && team.id !== game.team2_id
              );
            }
            
            if (availableTeams.length > 0) {
              const randomIndex = Math.floor(Math.random() * availableTeams.length);
              const team = availableTeams[randomIndex];
              
              game.referee_team_id = team.id;
              
              // Mark this team as having ref duty this week
              teamsWithRefDutyThisWeek[game.level_id].add(team.id);
            }
          }
        });
      }
      
      // Update the state with the randomly filled schedule
      dispatch({ 
        type: SET_SCHEDULE_DATA, 
        payload: {
          ...state,
          weeks: updatedWeeks
        }
      });
      
    } catch (error) {
      console.error('Error during random fill:', error);
      alert('Error during random fill: ' + error.message);
    } finally {
      setIsRandomFilling(false);
    }
  };

  return {
    isRandomFilling,
    randomFillSchedule
  };
};