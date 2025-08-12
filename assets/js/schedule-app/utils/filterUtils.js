import { isGameInPast } from './gameUtils';

export const filterGames = (games, weekMondayDate, filters, scheduleData) => {
  const { selectedLevels, selectedCourts, selectedReferees, selectedTeams, hidePastGames } = filters;
  
  return games.filter(game => {
    const levelMatch = selectedLevels.includes('all') || selectedLevels.includes(game.level_id.toString());
    
    const courtMatch = selectedCourts.includes('all') || selectedCourts.includes(game.court || 'No Court');
    
    const refereeValue = game.referee_name || 
      (game.referee_team_id ? 
        Object.values(scheduleData.teams_by_level)
          .flat()
          .find(team => team.id === game.referee_team_id)?.name || 'TBD'
        : 'TBD');
    const refereeMatch = selectedReferees.includes('all') || selectedReferees.includes(refereeValue);
    
    const teamMatch = selectedTeams.includes('all') || 
      selectedTeams.includes(game.team1_name) || 
      selectedTeams.includes(game.team2_name);
    
    const timeMatch = !hidePastGames || !isGameInPast(game, weekMondayDate);
    
    return levelMatch && courtMatch && refereeMatch && teamMatch && timeMatch;
  });
};

export const getFilterOptions = (scheduleData) => {
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