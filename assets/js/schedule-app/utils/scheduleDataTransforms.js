/**
 * Utility functions for transforming schedule data between different formats
 */

/**
 * Collects game assignments from schedule weeks
 * @param {Object} weeks - Schedule weeks object
 * @returns {Array} Array of game assignment objects
 */
export const collectGameAssignments = (weeks) => {
  const gameAssignments = [];
  
  if (!weeks || Object.keys(weeks).length === 0) {
    return gameAssignments;
  }
  
  for (const weekNum in weeks) {
    const weekData = weeks[weekNum];
    
    weekData.games.forEach(game => {
      if (game.isDeleted) {
        return;
      }
      
      let referee = game.referee_team_id || "";
      if (!referee && game.referee_name) {
        referee = game.referee_name;
      }
      
      gameAssignments.push({
        week: weekData.week_number,
        dayOfWeek: game.day_of_week,
        time: game.time,
        gameIndex: 0, // Will be determined based on time sorting
        level: game.level_id,
        team1: game.team1_id,
        team2: game.team2_id,
        referee: referee,
        court: game.court
      });
    });
  }
  
  return gameAssignments;
};

/**
 * Converts web format game assignments to backend schedule format
 * @param {Array} gameAssignments - Array of game assignment objects
 * @param {Object} state - Schedule state for ID-to-name conversion
 * @returns {Array} Array of week objects in backend format
 */
export const webToScheduleFormat = (gameAssignments, state = null) => {
  // First, group by week
  const weekGroups = {};
  gameAssignments.forEach(game => {
    const weekKey = game.week;
    
    if (!weekGroups[weekKey]) {
      weekGroups[weekKey] = {
        week: weekKey,
        slots: {}
      };
    }
    
    // Group times and create slots
    const timeStr = game.time;
    
    // Find or create slot number for this time
    let slotNum = 1;
    const slots = weekGroups[weekKey].slots;
    
    // Check if this time already has a slot number
    let foundSlot = false;
    for (const slotKey in slots) {
      const gamesInSlot = slots[slotKey];
      if (gamesInSlot.length > 0 && gamesInSlot[0].time === timeStr) {
        slotNum = parseInt(slotKey);
        foundSlot = true;
        break;
      }
    }
    
    // If no slot was found, create a new one with the next number
    if (!foundSlot) {
      slotNum = Object.keys(slots).length + 1;
    }
    
    // Initialize slot if needed
    if (!slots[slotNum]) {
      slots[slotNum] = [];
    }
    
    // Convert IDs to names if state is provided
    let levelName = game.level;
    let team1Name = game.team1;
    let team2Name = game.team2;
    let refName = game.referee;
    
    if (state) {
      // Convert level ID to name
      const level = state.levels.find(l => l.id == game.level); // Use == for type coercion
      levelName = level ? level.name : game.level;
      
      // Convert team IDs to names
      if (level && state.teamsByLevel[level.id]) {
        const team1Obj = state.teamsByLevel[level.id].find(t => t.id == game.team1);
        const team2Obj = state.teamsByLevel[level.id].find(t => t.id == game.team2);
        
        team1Name = team1Obj ? team1Obj.name : game.team1;
        team2Name = team2Obj ? team2Obj.name : game.team2;
        
        // Handle referee
        if (game.referee) {
          const refObj = state.teamsByLevel[level.id].find(t => t.id == game.referee);
          refName = refObj ? refObj.name : game.referee;
        }
      }
    }

    // Add the game to the slot
    slots[slotNum].push({
      level: levelName,
      teams: [team1Name, team2Name],
      ref: refName || "External Ref",
      time: timeStr // Add time for reference
    });
  });
  
  // Convert to array format for backend
  return Object.values(weekGroups);
};

/**
 * Collects week dates and off weeks from schedule weeks
 * @param {Object} weeks - Schedule weeks object
 * @returns {Object} Object with weekDates and offWeeks arrays
 */
export const collectWeekData = (weeks) => {
  const weekDates = [];
  const offWeeks = [];
  
  for (const weekNum in weeks) {
    const weekData = weeks[weekNum];
    
    const weekDate = {
      week_number: weekData.week_number,
      monday_date: weekData.monday_date,
      is_off_week: !!weekData.isOffWeek
    };
    
    // Include off week fields if this is an off week
    if (weekData.isOffWeek) {
      weekDate.title = weekData.title;
      weekDate.description = weekData.description;
      weekDate.has_basketball = weekData.has_basketball;
      
      // Debug logging
      console.log('collectWeekData - off week:', {
        week_number: weekData.week_number,
        title: weekData.title,
        description: weekData.description,
        has_basketball: weekData.has_basketball
      });
      
      offWeeks.push({
        week_number: weekData.week_number,
        monday_date: weekData.monday_date,
        title: weekData.title,
        description: weekData.description,
        has_basketball: weekData.has_basketball
      });
    }
    
    weekDates.push(weekDate);
  }
  
  return { weekDates, offWeeks };
};

/**
 * Prepares validation config from schedule state
 * @param {Object} state - Schedule context state
 * @returns {Object} Minimal config object for validation
 */
export const prepareValidationConfig = (state) => {
  const teams = state.teamsByLevel;
  const levels = [];
  const teams_per_level = {};
  
  for (let levelId of Object.keys(teams)) {
    if (teams[levelId].length > 0) {
      // Try to find level by matching either string ID (ScheduleCreate) or integer ID (ScheduleEdit)
      let level = state.levels.find(l => l.id === levelId); // Try string match first
      if (!level) {
        // Try integer match (for ScheduleEdit with API data)
        const levelIdInt = parseInt(levelId);
        level = state.levels.find(l => l.id === levelIdInt);
      }
      
      if (level) {
        levels.push(level.name);
        teams_per_level[level.name] = teams[levelId].length;
      }
    }
  }
  
  return { 
    levels: levels, 
    teams_per_level: teams_per_level 
  };
};

/**
 * Gets CSRF token from the DOM
 * @returns {string} CSRF token value
 */
export const getCsrfToken = () => {
  return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
};