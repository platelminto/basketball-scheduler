export const isGameInPast = (game, weekMondayDate) => {
  if (!game.time || game.day_of_week === null || game.day_of_week === undefined) {
    return false;
  }
  
  const gameDate = new Date(weekMondayDate);
  gameDate.setDate(gameDate.getDate() + game.day_of_week);
  
  const [hours, minutes] = game.time.split(':').map(num => parseInt(num, 10));
  gameDate.setHours(hours, minutes, 0, 0);
  
  return gameDate < new Date();
};

export const isGameCompleted = (game) => {
  return game.team1_score !== null && game.team1_score !== '' &&
         game.team2_score !== null && game.team2_score !== '';
};

export const getWinnerInfo = (game) => {
  if (!isGameCompleted(game)) return { team1Wins: false, team2Wins: false, tie: false };
  
  const score1 = parseInt(game.team1_score);
  const score2 = parseInt(game.team2_score);
  
  if (score1 > score2) return { team1Wins: true, team2Wins: false, tie: false };
  if (score2 > score1) return { team1Wins: false, team2Wins: true, tie: false };
  return { team1Wins: false, team2Wins: false, tie: true };
};

export const getDayName = (dayOfWeek) => {
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  return days[dayOfWeek] || '';
};

export const formatDate = (mondayDate, dayOfWeek) => {
  if (dayOfWeek === null || dayOfWeek === undefined) return '';
  
  const date = new Date(mondayDate);
  date.setDate(date.getDate() + dayOfWeek);
  return date.toLocaleDateString('en-GB', { 
    day: '2-digit', 
    month: '2-digit' 
  });
};

export const formatWeekHeader = (week) => {
  const mondayDate = new Date(week.monday_date);
  const dayName = mondayDate.toLocaleDateString('en-US', { weekday: 'long' });
  const dateStr = mondayDate.toLocaleDateString('en-US', { 
    month: 'long',
    day: 'numeric'
  });
  return `${dayName}, ${dateStr}`;
};

export const areAllGamesSameDay = (games) => {
  if (games.length === 0) return false;
  const firstDay = games[0].day_of_week;
  return games.every(game => game.day_of_week === firstDay);
};

export const getMostCommonWeekPattern = (scheduleData) => {
  if (!scheduleData) return [];
  
  const weekPatternCounts = {};
  
  Object.values(scheduleData.weeks).forEach(week => {
    if (!week.isOffWeek && week.games.length > 0) {
      const weekTimes = [...new Set(week.games
        .map(game => game.time)
        .filter(time => time))]
        .sort();
      
      const pattern = weekTimes.join(',');
      weekPatternCounts[pattern] = (weekPatternCounts[pattern] || 0) + 1;
    }
  });
  
  const mostCommonPattern = Object.entries(weekPatternCounts)
    .sort(([,a], [,b]) => b - a)[0];
  
  return mostCommonPattern ? mostCommonPattern[0].split(',') : [];
};

export const hasUnusualTimes = (week, commonWeekTimes) => {
  if (week.isOffWeek || commonWeekTimes.length === 0) return false;
  
  const weekTimes = [...new Set(week.games
    .map(game => game.time)
    .filter(time => time))]
    .sort();
  
  const isDifferent = weekTimes.length !== commonWeekTimes.length || 
    weekTimes.some(time => !commonWeekTimes.includes(time));
  
  return isDifferent;
};