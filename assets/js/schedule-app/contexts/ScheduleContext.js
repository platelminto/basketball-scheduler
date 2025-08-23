import React, { createContext, useReducer } from 'react';

// Create the context
export const ScheduleContext = createContext();

// Action types
export const SET_SEASON_LIST = 'SET_SEASON_LIST';
export const SET_CURRENT_SEASON = 'SET_CURRENT_SEASON';
export const SET_SCHEDULE_DATA = 'SET_SCHEDULE_DATA';
export const SET_TEAMS_DATA = 'SET_TEAMS_DATA';
export const UPDATE_SCHEDULE_DATA = 'UPDATE_SCHEDULE_DATA';
export const SET_LOADING = 'SET_LOADING';
export const SET_ERROR = 'SET_ERROR';

// Schedule Edit actions
export const UPDATE_GAME = 'UPDATE_GAME';
export const ADD_GAME = 'ADD_GAME';
export const DELETE_GAME = 'DELETE_GAME';
export const UPDATE_WEEK_DATE = 'UPDATE_WEEK_DATE';
export const DELETE_WEEK = 'DELETE_WEEK';
export const ADD_OFF_WEEK = 'ADD_OFF_WEEK';
export const ADD_NEW_WEEK = 'ADD_NEW_WEEK';
export const COPY_WEEK = 'COPY_WEEK';
export const MARK_CHANGED = 'MARK_CHANGED';
export const RESET_CHANGE_TRACKING = 'RESET_CHANGE_TRACKING';
export const TOGGLE_WEEK_LOCK = 'TOGGLE_WEEK_LOCK';

// Initial state
const initialState = {
  seasons: [],
  currentSeason: null,
  scheduleData: null,
  teamsData: null,
  isLoading: false,
  error: null,

  // Schedule edit properties
  season: null,
  weeks: {},
  levels: [],
  teamsByLevel: {},
  courts: [],
  changedGames: new Set(),
  newGames: new Set(),
  changedWeeks: new Set(),
  validationAffectingChanges: new Set(),
  lockedWeeks: new Set()
};

// Reducer function
const scheduleReducer = (state, action) => {
  switch (action.type) {
    case SET_SEASON_LIST:
      return {
        ...state,
        seasons: action.payload,
        isLoading: false
      };

    case SET_CURRENT_SEASON:
      return {
        ...state,
        currentSeason: action.payload,
        isLoading: false
      };

    case SET_SCHEDULE_DATA:
      // For schedule edit functionality
      if (action.payload.season && action.payload.weeks) {
        // Initialize the weeks data with isDeleted=false for all games
        const initializedWeeks = {};

        for (const weekId in action.payload.weeks) {
          const week = action.payload.weeks[weekId];
          // Initialize games with isDeleted flag
          const initializedGames = week.games.map(game => ({
            ...game,
            isDeleted: false
          }));

          initializedWeeks[weekId] = {
            ...week,
            games: initializedGames,
            // Ensure isOffWeek is preserved from API data
            isOffWeek: week.isOffWeek || false
          };

        }
        

        // The API uses teams_by_level but our internal structure uses teamsByLevel
        const teamsData = action.payload.teams_by_level || action.payload.teamsByLevel || {};
        
        // Initialize locked weeks - only if locks are not disabled
        const lockedWeeks = new Set();
        
        if (!action.payload.disableLocks) {
          const sortedWeeks = Object.values(initializedWeeks)
            .sort((a, b) => a.week_number - b.week_number)
            .filter(week => !week.isOffWeek); // Only consider non-off weeks
          
          const today = new Date();
          today.setHours(0, 0, 0, 0); // Reset time to start of day
          
          // Find the most recent week that has happened (today or past)
          let mostRecentHappenedWeek = null;
          for (let i = sortedWeeks.length - 1; i >= 0; i--) {
            const week = sortedWeeks[i];
            const weekDate = new Date(week.monday_date);
            weekDate.setHours(0, 0, 0, 0);
            
            // Only consider weeks that have happened (today or past)
            if (weekDate <= today) {
              mostRecentHappenedWeek = week;
              break;
            }
          }
          
          // Check if most recent week is more than 2 weeks old
          let lockAllWeeks = false;
          if (mostRecentHappenedWeek) {
            const weekDate = new Date(mostRecentHappenedWeek.monday_date);
            weekDate.setHours(0, 0, 0, 0);
            const twoWeeksAgo = new Date(today);
            twoWeeksAgo.setDate(today.getDate() - 14);
            
            if (weekDate < twoWeeksAgo) {
              lockAllWeeks = true;
            }
          }
          
          if (lockAllWeeks) {
            // Lock all weeks if most recent is more than 2 weeks old
            for (const week of sortedWeeks) {
              lockedWeeks.add(week.week_number);
            }
          } else {
            // Find the most recent week (today or in the past) that has incomplete scores
            let mostRecentIncompleteWeek = null;
            for (let i = sortedWeeks.length - 1; i >= 0; i--) {
              const week = sortedWeeks[i];
              const weekDate = new Date(week.monday_date);
              weekDate.setHours(0, 0, 0, 0);
              
              // Only consider weeks that have happened (today or past)
              if (weekDate > today) continue;
              
              const gamesWithBothScores = week.games.filter(game => 
                !game.isDeleted && 
                (game.team1_score !== null && game.team1_score !== undefined && game.team1_score !== '') && 
                (game.team2_score !== null && game.team2_score !== undefined && game.team2_score !== '')
              ).length;
              
              const totalActiveGames = week.games.filter(game => !game.isDeleted).length;
              const hasIncompleteScores = totalActiveGames > 0 && gamesWithBothScores < totalActiveGames;
              
              if (hasIncompleteScores) {
                mostRecentIncompleteWeek = week;
                break; // Found the most recent one, stop searching
              }
            }
            
            // Lock all weeks except the most recent incomplete one
            for (const week of sortedWeeks) {
              if (!mostRecentIncompleteWeek || week.week_number !== mostRecentIncompleteWeek.week_number) {
                lockedWeeks.add(week.week_number);
              }
            }
          }
        }
        
        return {
          ...state,
          season: action.payload.season,
          weeks: initializedWeeks,
          levels: action.payload.levels,
          teamsByLevel: teamsData,
          courts: action.payload.courts,
          lockedWeeks,
          isLoading: false
        };
      }

      // For general schedule data
      return {
        ...state,
        scheduleData: action.payload,
        isLoading: false
      };

    case SET_TEAMS_DATA:
      return {
        ...state,
        teamsData: action.payload,
        isLoading: false
      };

    case UPDATE_SCHEDULE_DATA:
      return {
        ...state,
        scheduleData: {
          ...state.scheduleData,
          ...action.payload
        },
        isLoading: false
      };

    case SET_LOADING:
      return {
        ...state,
        isLoading: action.payload
      };

    case SET_ERROR:
      return {
        ...state,
        error: action.payload,
        isLoading: false
      };


    case UPDATE_GAME: {
      const { gameId, field, value } = action.payload;
      const updatedWeeks = { ...state.weeks };

      // Find the week that contains this game
      for (const weekNum in updatedWeeks) {
        const weekData = updatedWeeks[weekNum];
        const gameIndex = weekData.games.findIndex(g => g.id === gameId);

        if (gameIndex !== -1) {
          // Create a new game object with the updated field
          const updatedGame = {
            ...weekData.games[gameIndex],
            [field]: value
          };

          // Create a new games array with the updated game
          const updatedGames = [...weekData.games];
          updatedGames[gameIndex] = updatedGame;

          // Update the week with the updated games array
          updatedWeeks[weekNum] = {
            ...weekData,
            games: updatedGames
          };

          break;
        }
      }

      return {
        ...state,
        weeks: updatedWeeks,
        validationCleared: true
      };
    }

    case MARK_CHANGED: {
      const gameId = action.payload;
      const changedGames = new Set(state.changedGames);
      changedGames.add(gameId);

      return {
        ...state,
        changedGames
      };
    }

    case ADD_GAME: {
      const { weekId, game } = action.payload;
      const updatedWeeks = { ...state.weeks };
      const weekData = updatedWeeks[weekId];

      if (weekData) {
        // Add the new game to the games array
        updatedWeeks[weekId] = {
          ...weekData,
          games: [...weekData.games, game]
        };

        // Add the game ID to newGames set
        const newGames = new Set(state.newGames);
        newGames.add(game.id);

        return {
          ...state,
          weeks: updatedWeeks,
          newGames
        };
      }

      return state;
    }

    case DELETE_GAME: {
      const { gameId, weekId, isCreationMode } = action.payload;
      const updatedWeeks = { ...state.weeks };
      const weekData = updatedWeeks[weekId];

      if (weekData) {
        const gameIndex = weekData.games.findIndex(g => g.id === gameId);

        if (gameIndex !== -1) {
          // In creation mode or for new games, just remove the game completely
          if (isCreationMode || state.newGames.has(gameId)) {
            // Remove the game from newGames set if it's there
            const newGames = new Set(state.newGames);
            newGames.delete(gameId);

            // Remove the game from the week's games array
            updatedWeeks[weekId] = {
              ...weekData,
              games: weekData.games.filter(g => g.id !== gameId)
            };

            return {
              ...state,
              weeks: updatedWeeks,
              newGames
            };
          } else {
            // For existing games in edit mode, toggle the isDeleted flag
            const updatedGame = {
              ...weekData.games[gameIndex],
              isDeleted: !weekData.games[gameIndex].isDeleted
            };

            // Update changedGames based on whether we're deleting or restoring
            const changedGames = new Set(state.changedGames);
            if (updatedGame.isDeleted) {
              // If we're deleting, remove from changedGames
              changedGames.delete(gameId);
            } else {
              // If we're restoring, add to changedGames
              changedGames.add(gameId);
            }

            // Create a new games array with the updated game
            const updatedGames = [...weekData.games];
            updatedGames[gameIndex] = updatedGame;

            // Update the week with the new games array
            updatedWeeks[weekId] = {
              ...weekData,
              games: updatedGames
            };

            return {
              ...state,
              weeks: updatedWeeks,
              changedGames
            };
          }
        }
      }

      return state;
    }

    case UPDATE_WEEK_DATE: {
      const { weekId, date, field, value, skipValidationClear } = action.payload;
      const updatedWeeks = { ...state.weeks };

      if (updatedWeeks[weekId]) {
        // Handle both legacy date updates and new field updates
        if (date) {
          // Legacy: Update the week's date
          updatedWeeks[weekId] = {
            ...updatedWeeks[weekId],
            monday_date: date
          };
        } else if (field && value !== undefined) {
          // New: Update any field
          updatedWeeks[weekId] = {
            ...updatedWeeks[weekId],
            [field]: value
          };
        }

        // Mark the week as changed
        const changedWeeks = new Set(state.changedWeeks);
        changedWeeks.add(weekId);

        // Track validation-affecting changes separately
        const validationAffectingChanges = new Set(state.validationAffectingChanges || []);
        if (!skipValidationClear) {
          validationAffectingChanges.add(weekId);
        }

        return {
          ...state,
          weeks: updatedWeeks,
          changedWeeks,
          validationAffectingChanges
        };
      }

      return state;
    }

    case DELETE_WEEK: {
      const { weekId } = action.payload;
      const updatedWeeks = { ...state.weeks };
      
      // Get the week being deleted to find its position
      const deletedWeek = updatedWeeks[weekId];
      if (!deletedWeek) return state; // Week doesn't exist
      
      // Remove the week
      delete updatedWeeks[weekId];
      
      // Get all remaining weeks sorted by week number
      const sortedWeeks = Object.values(updatedWeeks)
        .sort((a, b) => a.week_number - b.week_number);
      
      // Renumber all weeks sequentially and adjust dates for weeks after the deleted one
      const renumberedWeeks = {};
      const changedWeeks = new Set(state.changedWeeks);
      
      sortedWeeks.forEach((week, index) => {
        const newWeekNumber = index + 1;
        let adjustedDate = week.monday_date;
        let updatedGames = week.games || [];
        
        // For weeks that were after the deleted week, shift their dates back by 7 days
        if (week.week_number > deletedWeek.week_number) {
          const originalDate = new Date(week.monday_date);
          const shiftedDate = new Date(originalDate);
          shiftedDate.setDate(originalDate.getDate() - 7); // Shift back by 7 days
          adjustedDate = shiftedDate.toISOString().split('T')[0];
          
          // Update individual game dates for shifted weeks
          updatedGames = week.games.map(game => {
            if (game.day_of_week !== undefined && game.day_of_week !== null) {
              const gameDate = new Date(shiftedDate);
              gameDate.setDate(shiftedDate.getDate() + parseInt(game.day_of_week));
              return {
                ...game,
                date: gameDate.toISOString().split('T')[0]
              };
            }
            return game;
          });
        }
        
        const updatedWeek = {
          ...week,
          week_number: newWeekNumber,
          monday_date: adjustedDate,
          games: updatedGames
        };
        
        renumberedWeeks[newWeekNumber] = updatedWeek;
        
        // Mark affected weeks as changed
        if (week.week_number !== newWeekNumber || week.monday_date !== adjustedDate) {
          changedWeeks.add(newWeekNumber);
        }
      });
      
      // Mark the deleted week as changed (for backend deletion tracking)
      changedWeeks.add(weekId);
      
      return {
        ...state,
        weeks: renumberedWeeks,
        changedWeeks
      };
    }

    case ADD_OFF_WEEK: {
      const { afterWeekId, offWeekData } = action.payload;
      const updatedWeeks = { ...state.weeks };
      
      // Get all weeks sorted by week number
      const sortedWeeks = Object.values(updatedWeeks)
        .sort((a, b) => a.week_number - b.week_number);
      
      // Find insertion position
      let insertionIndex;
      if (afterWeekId === null) {
        // Insert at the beginning
        insertionIndex = 0;
      } else {
        // Find the index after the specified week
        const afterWeekIndex = sortedWeeks.findIndex(w => w.week_number === afterWeekId);
        insertionIndex = afterWeekIndex !== -1 ? afterWeekIndex + 1 : sortedWeeks.length;
      }
      
      // Create new off week with temporary ID
      const newOffWeek = {
        id: `off_week_${Date.now()}`,
        week_number: 0, // Will be set during renumbering
        monday_date: offWeekData.monday_date,
        isOffWeek: true,
        title: offWeekData.title || 'Off Week',
        description: offWeekData.description,
        has_basketball: offWeekData.has_basketball || false,
        start_time: offWeekData.start_time || '',
        end_time: offWeekData.end_time || '',
        show_times: offWeekData.show_times || false,
        games: []
      };
      
      // Insert the new off week into the sorted array
      sortedWeeks.splice(insertionIndex, 0, newOffWeek);
      
      // Renumber all weeks sequentially and adjust dates
      const renumberedWeeks = {};
      const changedWeeks = new Set(state.changedWeeks);
      
      sortedWeeks.forEach((week, index) => {
        const newWeekNumber = index + 1;
        let adjustedDate = week.monday_date;
        let updatedGames = week.games || [];
        
        // For weeks after the insertion point, shift their dates by 7 days
        if (index > insertionIndex) {
          const originalDate = new Date(week.monday_date);
          const shiftedDate = new Date(originalDate);
          shiftedDate.setDate(originalDate.getDate() + 7);
          adjustedDate = shiftedDate.toISOString().split('T')[0];
          
          // Update individual game dates for shifted weeks
          updatedGames = week.games.map(game => {
            if (game.day_of_week !== undefined && game.day_of_week !== null) {
              const gameDate = new Date(shiftedDate);
              gameDate.setDate(shiftedDate.getDate() + parseInt(game.day_of_week));
              return {
                ...game,
                date: gameDate.toISOString().split('T')[0]
              };
            }
            return game;
          });
        }
        
        const updatedWeek = {
          ...week,
          week_number: newWeekNumber,
          monday_date: adjustedDate,
          games: updatedGames
        };
        
        renumberedWeeks[newWeekNumber] = updatedWeek;
        
        // Mark all affected weeks as changed
        changedWeeks.add(newWeekNumber);
      });
      
      return {
        ...state,
        weeks: renumberedWeeks,
        changedWeeks
      };
    }

    case ADD_NEW_WEEK: {
      const { afterWeekId, newWeekData } = action.payload;
      const updatedWeeks = { ...state.weeks };
      
      // Get all weeks sorted by week number
      const sortedWeeks = Object.values(updatedWeeks)
        .sort((a, b) => a.week_number - b.week_number);
      
      // Find insertion position
      let insertionIndex;
      if (afterWeekId === null) {
        // Insert at the beginning
        insertionIndex = 0;
      } else {
        // Find the index after the specified week
        const afterWeekIndex = sortedWeeks.findIndex(w => w.week_number === afterWeekId);
        insertionIndex = afterWeekIndex !== -1 ? afterWeekIndex + 1 : sortedWeeks.length;
      }
      
      // Create new week with temporary ID
      const newWeek = {
        id: `new_week_${Date.now()}`,
        week_number: 0, // Will be set during renumbering
        monday_date: newWeekData.monday_date,
        games: newWeekData.games || [],
        isOffWeek: false
      };
      
      // Insert the new week into the sorted array
      sortedWeeks.splice(insertionIndex, 0, newWeek);
      
      // Renumber all weeks sequentially and adjust dates
      const renumberedWeeks = {};
      const changedWeeks = new Set(state.changedWeeks);
      
      sortedWeeks.forEach((week, index) => {
        const newWeekNumber = index + 1;
        
        // Calculate the appropriate Monday date for this week position
        let mondayDate;
        if (index === 0) {
          // First week - use the provided date or original date
          mondayDate = week.monday_date;
        } else {
          // Subsequent weeks - calculate based on previous week
          const prevWeekDate = new Date(sortedWeeks[index - 1].monday_date);
          const nextWeekDate = new Date(prevWeekDate);
          nextWeekDate.setDate(prevWeekDate.getDate() + 7);
          mondayDate = nextWeekDate.toISOString().split('T')[0];
        }
        
        // Update games' dates to match the new week date
        const updatedGames = week.games.map(game => {
          if (game.day_of_week !== undefined && game.day_of_week !== null) {
            const gameDate = new Date(mondayDate);
            gameDate.setDate(gameDate.getDate() + parseInt(game.day_of_week));
            return {
              ...game,
              date: gameDate.toISOString().split('T')[0]
            };
          }
          return game;
        });
        
        const updatedWeek = {
          ...week,
          week_number: newWeekNumber,
          monday_date: mondayDate,
          games: updatedGames
        };
        
        renumberedWeeks[newWeekNumber] = updatedWeek;
        
        // Mark all affected weeks as changed
        changedWeeks.add(newWeekNumber);
      });
      
      return {
        ...state,
        weeks: renumberedWeeks,
        changedWeeks
      };
    }

    case COPY_WEEK: {
      const { afterWeekId, templateWeek } = action.payload;
      const updatedWeeks = { ...state.weeks };
      
      // Get all weeks sorted by week number
      const sortedWeeks = Object.values(updatedWeeks)
        .sort((a, b) => a.week_number - b.week_number);
      
      // Find insertion position
      let insertionIndex;
      if (afterWeekId === null) {
        // Insert at the beginning
        insertionIndex = 0;
      } else {
        // Find the index after the specified week
        const afterWeekIndex = sortedWeeks.findIndex(w => w.week_number === afterWeekId);
        insertionIndex = afterWeekIndex !== -1 ? afterWeekIndex + 1 : sortedWeeks.length;
      }
      
      // Calculate the appropriate date for the new week
      let newWeekDate;
      if (insertionIndex === 0) {
        // Inserting at the beginning - use one week before the first week
        if (sortedWeeks.length > 0) {
          const firstWeekDate = new Date(sortedWeeks[0].monday_date);
          const prevWeekDate = new Date(firstWeekDate);
          prevWeekDate.setDate(firstWeekDate.getDate() - 7);
          newWeekDate = prevWeekDate.toISOString().split('T')[0];
        } else {
          // No existing weeks, use current Monday
          const currentDate = new Date();
          const dayOfWeek = currentDate.getDay();
          const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
          currentDate.setDate(currentDate.getDate() + daysUntilMonday);
          newWeekDate = currentDate.toISOString().split('T')[0];
        }
      } else if (insertionIndex >= sortedWeeks.length) {
        // Inserting at the end - use one week after the last week
        const lastWeekDate = new Date(sortedWeeks[sortedWeeks.length - 1].monday_date);
        const nextWeekDate = new Date(lastWeekDate);
        nextWeekDate.setDate(lastWeekDate.getDate() + 7);
        newWeekDate = nextWeekDate.toISOString().split('T')[0];
      } else {
        // Inserting between weeks - use the date where we're inserting
        newWeekDate = sortedWeeks[insertionIndex].monday_date;
      }
      
      // Create new week by copying template
      const newWeek = {
        id: `copied_week_${Date.now()}`,
        week_number: 0, // Will be set during renumbering
        monday_date: newWeekDate,
        games: templateWeek.games.map(game => ({
          ...game,
          id: `new_${Date.now()}_${Math.random()}`,
          date: new Date(newWeekDate).toISOString().split('T')[0] // Will be updated with proper day offset below
        })),
        isOffWeek: false
      };
      
      // Insert the new week into the sorted array
      sortedWeeks.splice(insertionIndex, 0, newWeek);
      
      // Renumber all weeks sequentially and adjust dates
      const renumberedWeeks = {};
      const changedWeeks = new Set(state.changedWeeks);
      
      sortedWeeks.forEach((week, index) => {
        const newWeekNumber = index + 1;
        
        // Calculate the appropriate Monday date for this week position
        let mondayDate;
        if (index === 0) {
          // First week - use the calculated date
          mondayDate = week.monday_date;
        } else {
          // Subsequent weeks - calculate based on previous week
          const prevWeekDate = new Date(sortedWeeks[index - 1].monday_date);
          const nextWeekDate = new Date(prevWeekDate);
          nextWeekDate.setDate(prevWeekDate.getDate() + 7);
          mondayDate = nextWeekDate.toISOString().split('T')[0];
        }
        
        // Update games' dates to match the new week date
        const updatedGames = week.games.map(game => {
          if (game.day_of_week !== undefined && game.day_of_week !== null) {
            const gameDate = new Date(mondayDate);
            gameDate.setDate(gameDate.getDate() + parseInt(game.day_of_week));
            return {
              ...game,
              date: gameDate.toISOString().split('T')[0]
            };
          }
          return game;
        });
        
        const updatedWeek = {
          ...week,
          week_number: newWeekNumber,
          monday_date: mondayDate,
          games: updatedGames
        };
        
        renumberedWeeks[newWeekNumber] = updatedWeek;
        
        // Mark all affected weeks as changed
        changedWeeks.add(newWeekNumber);
      });
      
      return {
        ...state,
        weeks: renumberedWeeks,
        changedWeeks
      };
    }

    case RESET_CHANGE_TRACKING:
      return {
        ...state,
        changedGames: new Set(),
        newGames: new Set(),
        changedWeeks: new Set(),
        validationAffectingChanges: new Set()
      };

    case TOGGLE_WEEK_LOCK: {
      const { weekNumber } = action.payload;
      const lockedWeeks = new Set(state.lockedWeeks);
      
      if (lockedWeeks.has(weekNumber)) {
        lockedWeeks.delete(weekNumber);
      } else {
        lockedWeeks.add(weekNumber);
      }
      
      return {
        ...state,
        lockedWeeks
      };
    }
      
    default:
      return state;
  }
};

// Provider component
export const ScheduleProvider = ({ children }) => {
  const [state, dispatch] = useReducer(scheduleReducer, initialState);

  return (
    <ScheduleContext.Provider value={{ state, dispatch }}>
      {children}
    </ScheduleContext.Provider>
  );
};