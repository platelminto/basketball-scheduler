import React, { useEffect } from 'react';

const ValidationResults = ({ 
  validationResults, 
  ignoredFailures, 
  onIgnoreFailure, 
  allPassedOrIgnored,
  onValidationChange // New prop to trigger parent updates
}) => {
  // Add useEffect to notify parent component when validation status changes
  useEffect(() => {
    // If parent provided an update callback, call it whenever allPassedOrIgnored changes
    if (onValidationChange && validationResults) {
      onValidationChange(allPassedOrIgnored);
    }
  }, [allPassedOrIgnored, validationResults, onValidationChange]);

  if (!validationResults) return null;

  // Define explanations for each validation
  const explanations = {
    'Pairings': 'Teams must play against other teams in their level a specific number of times based on level size.',
    'Cycle Pairings': 'Matchups must repeat in proper round-robin cycles throughout the season.',
    'Referee-Player': 'A team cannot referee any game in which they are playing.',
    'Adjacent Slots': 'Teams can only referee games in time slots that are directly before or after their own game.',
    'sequential_week_dates': 'Schedule must have a week (game week or off week) at every Monday from first to last week with no gaps.'
  };

  // Track not just any failures, but also how many are ignored
  let hasFailures = false;
  let hasIgnoredFailures = false;
  let allFailuresIgnored = true;
  
  Object.entries(validationResults).forEach(([testName, result]) => {
    if (!result.passed) {
      hasFailures = true;
      if (ignoredFailures.has(testName)) {
        hasIgnoredFailures = true;
      } else {
        allFailuresIgnored = false;
      }
    }
  });

  return (
    <div className="validation-results-container mb-4">
      <h3 className="mb-3">Validation Results</h3>
      
      {Object.entries(validationResults).map(([testName, result]) => {
        
        // Determine styling based on pass/fail/ignore status
        const isIgnored = !result.passed && ignoredFailures.has(testName);
        const borderClass = result.passed ? 'border-success' : (isIgnored ? 'border-warning' : 'border-danger');
        const iconClass = result.passed ? 'fa-check-circle text-success' : 
                         (isIgnored ? 'fa-exclamation-triangle text-warning' : 'fa-times-circle text-danger');
        const badgeClass = result.passed ? 'bg-success' : (isIgnored ? 'bg-warning' : 'bg-danger');
        const statusText = result.passed ? 'Passed' : (isIgnored ? 'Ignored' : 'Failed');
        
        return (
          <div 
            key={testName}
            className={`mb-3 p-3 border rounded ${borderClass}`}
          >
            <h5 className="mb-1">
              <i className={`fas ${iconClass} me-2`}></i>
              {testName === 'sequential_week_dates' ? 'Sequential Week Dates' : testName} 
              <span className={`badge ${badgeClass} ms-2`}>
                {statusText}
              </span>
            </h5>
            
            <p className="mb-1 small">{explanations[testName] || 'No description available.'}</p>
            
            {!result.passed && result.errors && (
              <ul className="list-unstyled mt-2 mb-0 small text-muted">
                {result.errors.slice(0, 5).map((error, index) => (
                  <li key={index}>
                    <i className="fas fa-exclamation-triangle text-warning me-1"></i> {error}
                  </li>
                ))}
                {result.errors.length > 5 && (
                  <li>...and {result.errors.length - 5} more</li>
                )}
              </ul>
            )}
            
            {!result.passed && (
              <div className="form-check mt-2">
                <input 
                  className="form-check-input" 
                  type="checkbox" 
                  id={`ignore-${testName}`}
                  checked={ignoredFailures.has(testName)}
                  onChange={(e) => onIgnoreFailure(testName, e.target.checked)}
                />
                <label className="form-check-label small" htmlFor={`ignore-${testName}`}>
                  Ignore this failure
                </label>
              </div>
            )}
          </div>
        );
      })}
      
      <div className={`mt-4 alert ${
        !hasFailures ? 'alert-success' : 
        (hasFailures && hasIgnoredFailures && allFailuresIgnored) ? 'alert-warning' : 
        'alert-danger'}`}
      >
        {!hasFailures && (
          <>
            <strong><i className="fas fa-thumbs-up"></i> All validation checks passed!</strong> 
            <span> Schedule is valid and ready to be saved.</span>
          </>
        )}
        
        {hasFailures && hasIgnoredFailures && allFailuresIgnored && (
          <>
            <strong><i className="fas fa-exclamation-triangle"></i> Some validation checks failed but are ignored.</strong> 
            <span> You can now save the schedule, but review ignored issues.</span>
          </>
        )}
        
        {hasFailures && !allFailuresIgnored && (
          <>
            <strong><i className="fas fa-times-circle"></i> Some validation checks failed.</strong> 
            <span> Please review the errors above or check "Ignore this failure" to proceed.</span>
          </>
        )}
      </div>
    </div>
  );
};

export default ValidationResults;