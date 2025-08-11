/**
 * Utility functions for week and date management
 */

/**
 * Formats a date object to YYYY-MM-DD string
 * @param {Date} date - Date object to format
 * @returns {string} Formatted date string
 */
export const formatDate = (date) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

/**
 * Gets the day name from a date string
 * @param {string} date - Date string
 * @returns {string} Day name (e.g., "Monday")
 */
export const getDayName = (date) => {
  return new Date(date).toLocaleDateString('en-US', { weekday: 'long' });
};

/**
 * Finds the next Monday date after the last week in the schedule
 * @param {Object} weeks - Schedule weeks object
 * @returns {Date} Date object for next Monday
 */
export const findNextWeekDate = (weeks) => {
  // Find the last week in the schedule
  const weekNumbers = Object.keys(weeks).map(Number);
  if (weekNumbers.length === 0) {
    // If no weeks exist, start from next Monday
    const date = new Date();
    while (date.getDay() !== 1) {
      date.setDate(date.getDate() + 1);
    }
    return date;
  }

  const lastWeekNum = Math.max(...weekNumbers);
  const lastWeek = weeks[lastWeekNum];
  
  // Calculate one week after the last week's date
  const date = new Date(lastWeek.monday_date);
  date.setDate(date.getDate() + 7);
  return date;
};

/**
 * Creates a new week object with optional template
 * @param {Object} weeks - Current weeks object
 * @param {Object} templateWeek - Optional week to copy games from
 * @returns {Object} New week object
 */
export const createNewWeek = (weeks, templateWeek = null) => {
  const startDate = findNextWeekDate(weeks);
  const formattedDate = formatDate(startDate);
  const nextWeekNum = Object.keys(weeks).length + 1;
  
  const newWeek = {
    id: nextWeekNum,
    week_number: nextWeekNum,
    monday_date: formattedDate,
    games: []
  };
  
  // If using a template, copy games with appropriate modifications
  if (templateWeek) {
    templateWeek.games.forEach(game => {
      if (!game.isDeleted) {
        const newGameId = `new_${Date.now()}_${Math.random()}`;
        const gameClone = {
          ...game,
          id: newGameId,
          team1_score: '',
          team2_score: ''
        };
        newWeek.games.push(gameClone);
      }
    });
  }
  
  return newWeek;
};

/**
 * Creates a new off week object
 * @param {Object} weeks - Current weeks object
 * @returns {Object} New off week object
 */
export const createOffWeek = (weeks) => {
  const startDate = findNextWeekDate(weeks);
  const formattedDate = formatDate(startDate);
  const nextWeekNum = Object.keys(weeks).length + 1;
  
  return {
    id: nextWeekNum,
    week_number: nextWeekNum,
    monday_date: formattedDate,
    games: [],
    isOffWeek: true
  };
};

/**
 * Finds the last non-off week from the schedule
 * @param {Object} weeks - Schedule weeks object
 * @returns {Object|null} Last normal week or null if none found
 */
export const findLastNormalWeek = (weeks) => {
  const weekNumbers = Object.keys(weeks).map(Number);
  if (weekNumbers.length === 0) return null;
  
  // Sort week numbers in descending order
  const sortedWeekNumbers = weekNumbers.sort((a, b) => b - a);
  
  // Find the last non-off week
  for (const weekNum of sortedWeekNumbers) {
    const week = weeks[weekNum];
    if (!week.isOffWeek) {
      return week;
    }
  }
  
  return null;
};

/**
 * Creates a default week with Monday time slots
 * @param {string} startDate - Optional start date (YYYY-MM-DD format)
 * @returns {Object} Default week with games
 */
export const createDefaultWeek = (startDate = null) => {
  // Default to next Monday for the first week if no date provided
  let date;
  if (startDate) {
    date = new Date(startDate);
  } else {
    date = new Date();
    while (date.getDay() !== 1) {
      date.setDate(date.getDate() + 1);
    }
  }
  
  const formattedDate = formatDate(date);
  
  // Create a new week
  const newWeek = {
    id: 1,
    week_number: 1,
    monday_date: formattedDate,
    games: []
  };
  
  // Create a default Monday with specific court counts
  const defaultTimes = [
    { time: '18:10', courts: 2 },
    { time: '19:20', courts: 2 },
    { time: '20:30', courts: 2 },
    { time: '21:40', courts: 3 }
  ];
  
  // Add each default time slot
  defaultTimes.forEach(timeSlot => {
    for (let i = 0; i < timeSlot.courts; i++) {
      const gameId = `new_${Date.now()}_${Math.random()}`;
      const gameDate = new Date(formattedDate);
      
      newWeek.games.push({
        id: gameId,
        day_of_week: 0, // Monday (0-based)
        time: timeSlot.time,
        court: `Court ${i+1}`,
        date: gameDate.toISOString().split('T')[0],
        level_id: '',
        level_name: '',
        team1_id: '',
        team1_name: '',
        team2_id: '',
        team2_name: '',
        team1_score: '',
        team2_score: '',
        referee_team_id: '',
        referee_name: '',
        isDeleted: false
      });
    }
  });
  
  return newWeek;
};

/**
 * Scrolls to a specific week element
 * @param {number|string} weekId - Week ID to scroll to
 */
export const scrollToWeek = (weekId) => {
  setTimeout(() => {
    const weekElement = document.querySelector(`[data-week-id="${weekId}"]`);
    if (weekElement) {
      weekElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, 100);
};