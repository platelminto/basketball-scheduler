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
export const TOGGLE_EDIT_MODE = 'TOGGLE_EDIT_MODE';
export const UPDATE_GAME = 'UPDATE_GAME';
export const ADD_GAME = 'ADD_GAME';
export const DELETE_GAME = 'DELETE_GAME';
export const UPDATE_WEEK_DATE = 'UPDATE_WEEK_DATE';
export const MARK_CHANGED = 'MARK_CHANGED';
export const RESET_CHANGE_TRACKING = 'RESET_CHANGE_TRACKING';

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
  editingEnabled: false,
  changedGames: new Set(),
  newGames: new Set(),
  changedWeeks: new Set()
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
            games: initializedGames
          };
        }
        

        // The API uses teams_by_level but our internal structure uses teamsByLevel
        const teamsData = action.payload.teams_by_level || action.payload.teamsByLevel || {};
        
        return {
          ...state,
          season: action.payload.season,
          weeks: initializedWeeks,
          levels: action.payload.levels,
          teamsByLevel: teamsData,
          courts: action.payload.courts,
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

    case TOGGLE_EDIT_MODE:
      return {
        ...state,
        editingEnabled: action.payload
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
      const { weekId, date } = action.payload;
      const updatedWeeks = { ...state.weeks };

      if (updatedWeeks[weekId]) {
        // Update the week's date
        updatedWeeks[weekId] = {
          ...updatedWeeks[weekId],
          monday_date: date
        };

        // Mark the week as changed
        const changedWeeks = new Set(state.changedWeeks);
        changedWeeks.add(weekId);

        return {
          ...state,
          weeks: updatedWeeks,
          changedWeeks
        };
      }

      return state;
    }

    case RESET_CHANGE_TRACKING:
      return {
        ...state,
        changedGames: new Set(),
        newGames: new Set(),
        changedWeeks: new Set()
      };
      
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