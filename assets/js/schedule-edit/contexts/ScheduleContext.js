import React, { createContext, useReducer } from 'react';

// Create the context
export const ScheduleContext = createContext();

// Action types
export const TOGGLE_EDIT_MODE = 'TOGGLE_EDIT_MODE';
export const SET_SCHEDULE_DATA = 'SET_SCHEDULE_DATA';
export const UPDATE_GAME = 'UPDATE_GAME';
export const ADD_GAME = 'ADD_GAME';
export const DELETE_GAME = 'DELETE_GAME';
export const UPDATE_WEEK_DATE = 'UPDATE_WEEK_DATE';
export const MARK_CHANGED = 'MARK_CHANGED';

// Initial state
const initialState = {
  season: null,
  weeks: {},
  levels: [],
  teamsByLevel: {},
  courts: [],
  editingEnabled: false,
  changedGames: new Set(),
  newGames: new Set(),
  deletedGames: new Set(),
  changedWeeks: new Set(),
  isLoading: true,
  error: null
};

// Reducer function
const scheduleReducer = (state, action) => {
  switch (action.type) {
    case SET_SCHEDULE_DATA:
      return {
        ...state,
        season: action.payload.season,
        weeks: action.payload.weeks,
        levels: action.payload.levels,
        teamsByLevel: action.payload.teams_by_level,
        courts: action.payload.courts,
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
        weeks: updatedWeeks
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
      const { gameId, weekId } = action.payload;

      // Add the game ID to deletedGames set - don't remove from UI yet
      // This will be handled on save
      if (!state.newGames.has(gameId)) {
        const deletedGames = new Set(state.deletedGames);
        deletedGames.add(gameId);

        // Remove from changedGames if it was there
        const changedGames = new Set(state.changedGames);
        changedGames.delete(gameId);

        return {
          ...state,
          deletedGames,
          changedGames
        };
      } else {
        // If it's a new game, remove it from newGames
        const newGames = new Set(state.newGames);
        newGames.delete(gameId);

        // For new games that haven't been saved yet, we can safely remove them from UI
        const updatedWeeks = { ...state.weeks };
        const weekData = updatedWeeks[weekId];

        if (weekData) {
          // Remove the game from the games array
          updatedWeeks[weekId] = {
            ...weekData,
            games: weekData.games.filter(g => g.id !== gameId)
          };
        }

        return {
          ...state,
          weeks: updatedWeeks,
          newGames
        };
      }
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