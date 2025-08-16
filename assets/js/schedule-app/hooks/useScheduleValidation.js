import { useState, useCallback } from 'react';
import { collectGameAssignments, webToScheduleFormat, prepareValidationConfig, getCsrfToken } from '../utils/scheduleDataTransforms';

/**
 * Custom hook for managing schedule validation
 * @param {Object} state - Schedule context state
 * @param {boolean} showValidation - Whether validation should be performed
 * @param {boolean} initialShowSaveButton - Initial state for save button
 * @returns {Object} Validation state and functions
 */
export const useScheduleValidation = (state, showValidation = false, initialShowSaveButton = false) => {
  const [validationResults, setValidationResults] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [ignoredFailures, setIgnoredFailures] = useState(new Set());
  const [showSaveButton, setShowSaveButton] = useState(initialShowSaveButton);

  /**
   * Validates sequential week dates (client-side validation)
   */
  const validateSequentialWeekDates = useCallback(() => {
    const errors = [];
    
    if (!state.weeks || Object.keys(state.weeks).length === 0) {
      return { passed: true, errors: [] };
    }

    // Extract all week dates
    const weekDates = [];
    for (const weekNum in state.weeks) {
      const week = state.weeks[weekNum];
      if (week.monday_date) {
        try {
          const dateObj = new Date(week.monday_date);
          if (isNaN(dateObj.getTime())) {
            errors.push(`Week ${weekNum}: Invalid date format '${week.monday_date}'`);
            continue;
          }
          weekDates.push({
            weekNum: parseInt(weekNum),
            date: dateObj,
            isOffWeek: week.isOffWeek || false
          });
        } catch (e) {
          errors.push(`Week ${weekNum}: Error parsing date '${week.monday_date}'`);
        }
      }
    }

    if (weekDates.length === 0) {
      return { passed: true, errors: [] };
    }

    // Sort by date
    weekDates.sort((a, b) => a.date - b.date);
    
    const firstDate = weekDates[0].date;
    const lastDate = weekDates[weekDates.length - 1].date;
    
    // Calculate expected number of weeks
    const dateDiff = lastDate - firstDate;
    const expectedWeeks = Math.floor(dateDiff / (7 * 24 * 60 * 60 * 1000)) + 1;
    
    if (weekDates.length !== expectedWeeks) {
      errors.push(`Schedule has ${weekDates.length} weeks but should have ${expectedWeeks} weeks from ${firstDate.toDateString()} to ${lastDate.toDateString()}`);
    }

    // Check that each Monday is exactly 7 days after the previous
    for (let i = 1; i < weekDates.length; i++) {
      const prevWeek = weekDates[i-1];
      const currWeek = weekDates[i];
      
      // Compare dates by converting to date strings to avoid DST time issues
      const prevDateStr = prevWeek.date.toDateString();
      const currDateStr = currWeek.date.toDateString();
      
      const expectedDate = new Date(prevWeek.date);
      expectedDate.setDate(expectedDate.getDate() + 7);
      const expectedDateStr = expectedDate.toDateString();
      
      if (currDateStr !== expectedDateStr) {
        const gapDays = Math.floor((currWeek.date - prevWeek.date) / (24 * 60 * 60 * 1000));
        
        if (gapDays > 7) {
          errors.push(`Gap detected: Week ${prevWeek.weekNum} (${prevWeek.date.toDateString()}) to Week ${currWeek.weekNum} (${currWeek.date.toDateString()}) - missing ${gapDays - 7} days`);
        } else if (gapDays < 7) {
          errors.push(`Date sequence error: Week ${prevWeek.weekNum} (${prevWeek.date.toDateString()}) to Week ${currWeek.weekNum} (${currWeek.date.toDateString()}) - ${gapDays} days apart (should be 7)`);
        }
        // If gapDays === 7 but dates don't match, it's likely just a DST issue, so we don't error
      }
    }

    // Verify each date falls on a Monday
    for (const { weekNum, date } of weekDates) {
      if (date.getDay() !== 1) { // 1 = Monday
        const weekdayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const actualDay = weekdayNames[date.getDay()];
        errors.push(`Week ${weekNum}: Date ${date.toDateString()} is a ${actualDay}, not a Monday`);
      }
    }

    return {
      passed: errors.length === 0,
      errors: errors
    };
  }, [state.weeks]);

  /**
   * Validates the current schedule
   */
  const validateSchedule = useCallback(async () => {
    
    setIsValidating(true);
    setValidationResults(null);
    
    try {
      // First run client-side validations
      const sequentialDatesResult = validateSequentialWeekDates();
      
      // Start with client-side results
      const clientSideResults = {
        'sequential_week_dates': sequentialDatesResult
      };

      // Collect game assignments
      const gameAssignments = collectGameAssignments(state.weeks);
      
      // Convert to backend format
      const scheduleData = webToScheduleFormat(gameAssignments, state);
      
      // Prepare validation config
      const minimalConfig = prepareValidationConfig(state);
      
      // Call validation API
      const response = await fetch('/scheduler/api/seasons/validate/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
          schedule: scheduleData,
          config: minimalConfig
        })
      });
      
      const serverSideData = await response.json();
      
      // Merge client-side and server-side validation results
      const combinedResults = {
        ...clientSideResults,
        ...serverSideData
      };
      
      setValidationResults(combinedResults);
      
      // Check validation state with the combined data
      let allPassedOrIgnored = true;
      for (const testName in combinedResults) {
        if (!combinedResults[testName].passed && !ignoredFailures.has(testName)) {
          allPassedOrIgnored = false;
          break;
        }
      }
      setShowSaveButton(allPassedOrIgnored);
    } catch (error) {
      console.error('Error validating schedule:', error);
      alert('Error during validation: ' + error.message);
    }
    
    setIsValidating(false);
  }, [state]);

  /**
   * Checks if all validation tests pass or are ignored
   * @param {Object} results - Validation results to check
   */
  const checkValidationState = useCallback((results = validationResults) => {
    if (!results) return;

    let allPassedOrIgnored = true;
    
    for (const testName in results) {
      if (!results[testName].passed && !ignoredFailures.has(testName)) {
        allPassedOrIgnored = false;
        break;
      }
    }

    setShowSaveButton(allPassedOrIgnored);
  }, [validationResults, ignoredFailures]);

  /**
   * Handles ignoring or un-ignoring validation failures
   * @param {string} testName - Name of the test to ignore/unignore
   * @param {boolean} isIgnored - Whether the test should be ignored
   */
  const handleIgnoreFailure = useCallback((testName, isIgnored) => {
    // Create a new Set to ensure state update is detected
    const updatedIgnores = new Set(ignoredFailures);
    
    if (isIgnored) {
      updatedIgnores.add(testName);
    } else {
      updatedIgnores.delete(testName);
    }
    
    setIgnoredFailures(updatedIgnores);
    
    // Directly calculate the new validation state
    let allPassedOrIgnored = true;
    
    if (validationResults) {
      for (const name in validationResults) {
        // A test fails validation if it failed and is not in the updated ignore set
        if (!validationResults[name].passed && !updatedIgnores.has(name)) {
          allPassedOrIgnored = false;
          break;
        }
      }
    }
    
    // Update button state immediately
    setShowSaveButton(allPassedOrIgnored);
  }, [ignoredFailures, validationResults]);

  /**
   * Clears validation results and resets state
   */
  const clearValidationResults = useCallback(() => {
    setValidationResults(null);
    setIgnoredFailures(new Set());
    setShowSaveButton(false);
  }, []);

  /**
   * Resets validation state to initial values
   * @param {boolean} defaultSaveButtonState - Default state for save button
   */
  const resetValidationState = useCallback((defaultSaveButtonState = false) => {
    setValidationResults(null);
    setIgnoredFailures(new Set());
    setShowSaveButton(defaultSaveButtonState);
  }, []);

  return {
    // State
    validationResults,
    isValidating,
    ignoredFailures,
    showSaveButton,
    
    // Functions
    validateSchedule,
    handleIgnoreFailure,
    clearValidationResults,
    resetValidationState,
    checkValidationState
  };
};