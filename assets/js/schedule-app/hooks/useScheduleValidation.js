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
   * Validates the current schedule
   */
  const validateSchedule = useCallback(async () => {
    
    setIsValidating(true);
    setValidationResults(null);
    
    try {
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
      
      const data = await response.json();
      setValidationResults(data);
      
      // Check validation state with the new data
      let allPassedOrIgnored = true;
      for (const testName in data) {
        if (!data[testName].passed && !ignoredFailures.has(testName)) {
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