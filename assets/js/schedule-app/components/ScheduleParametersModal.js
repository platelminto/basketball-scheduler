import React, { useState, useEffect } from 'react';

const ScheduleParametersModal = ({ 
  isOpen, 
  onClose, 
  onGenerate, 
  setupData 
}) => {
  const [parameters, setParameters] = useState({
    min_referee_count: 4,
    max_referee_count: 6,
    slot_limits: {
      1: 3,
      2: 4,
      3: 4,
      4: 4
    },
    time_limit: 60,
    // Advanced options
    num_blueprints_to_generate: '',
    gapRel: 0.25
  });

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [abortController, setAbortController] = useState(null);

  // Cancel generation if page is unloaded
  useEffect(() => {
    const handleBeforeUnload = async () => {
      if (isGenerating && abortController) {
        // Cancel the generation
        abortController.abort();
        
        // Signal backend to stop
        try {
          await fetch('/scheduler/api/seasons/cancel-generation/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCsrfToken(),
            }
          });
        } catch (error) {
          console.log('Cancellation request error on unload:', error);
        }
      }
    };

    if (isGenerating) {
      window.addEventListener('beforeunload', handleBeforeUnload);
      return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }
  }, [isGenerating, abortController]);

  const handleParameterChange = (key, value) => {
    setParameters(prev => ({
      ...prev,
      [key]: value === '' ? '' : (key === 'gapRel' ? parseFloat(value) : parseInt(value))
    }));
  };

  const handleSlotLimitChange = (slot, value) => {
    setParameters(prev => ({
      ...prev,
      slot_limits: {
        ...prev.slot_limits,
        [slot]: value === '' ? '' : parseInt(value)
      }
    }));
  };

  const handleGenerate = async () => {
    // Validate all fields are filled
    const emptyFields = [];
    
    if (parameters.min_referee_count === '') emptyFields.push('Minimum Referee Count');
    if (parameters.max_referee_count === '') emptyFields.push('Maximum Referee Count');
    if (parameters.time_limit === '') emptyFields.push('Time Limit');
    // num_blueprints_to_generate is optional - backend handles default
    if (parameters.gapRel === '') emptyFields.push('Relative Gap Tolerance');
    
    // Check slot limits
    for (const [slot, value] of Object.entries(parameters.slot_limits)) {
      if (value === '') emptyFields.push(`Slot ${slot} Limit`);
    }
    
    if (emptyFields.length > 0) {
      alert(`Please fill in all fields:\n• ${emptyFields.join('\n• ')}`);
      return;
    }
    
    // Create new AbortController for this generation
    const controller = new AbortController();
    setAbortController(controller);
    
    setIsGenerating(true);
    setElapsedTime(0);
    
    // Start the simple time counter
    const timeInterval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
    
    try {
      await onGenerate(parameters, controller.signal);
      
      // Only proceed if not cancelled
      if (!controller.signal.aborted) {
        clearInterval(timeInterval);
        setIsGenerating(false);
        setElapsedTime(0);
        setAbortController(null);
        onClose();
      }
    } catch (error) {
      clearInterval(timeInterval);
      
      // Check if this was a user cancellation
      if (error.name === 'AbortError') {
        // Brief delay then reset
        setTimeout(() => {
          setIsGenerating(false);
          setElapsedTime(0);
          setAbortController(null);
        }, 500);
      } else {
        // Actual error - reset immediately
        setIsGenerating(false);
        setElapsedTime(0);
        setAbortController(null);
        // Error handling is done by the parent component
      }
    }
  };

  const handleCancel = async () => {
    if (isGenerating && abortController) {
      // Abort the frontend request
      abortController.abort();
      
      // Also signal the backend to stop processing
      try {
        await fetch('/scheduler/api/seasons/cancel-generation/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          }
        });
      } catch (error) {
        // Ignore errors for cancellation request
        console.log('Cancellation request error (ignored):', error);
      }
    } else {
      // Not generating, just close
      onClose();
    }
  };

  // Helper function to get CSRF token
  const getCsrfToken = () => {
    return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  };

  const getNumSlots = () => {
    if (!setupData || !setupData.schedule || !setupData.schedule.weeks) return 4;
    
    // Find the maximum number of time slots across all weeks
    let maxSlots = 0;
    setupData.schedule.weeks.forEach(week => {
      if (!week.isOffWeek && week.days) {
        week.days.forEach(day => {
          if (day.times) {
            maxSlots = Math.max(maxSlots, day.times.length);
          }
        });
      }
    });
    
    return Math.max(maxSlots, 4); // Default to 4 if no data found
  };

  const numSlots = getNumSlots();

  if (!isOpen) return null;

  return (
    <div className="modal" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Schedule Generation Parameters</h5>
            {!isGenerating && (
              <button 
                type="button" 
                className="btn-close" 
                onClick={onClose}
                aria-label="Close"
              ></button>
            )}
          </div>

          <div className="modal-body">
            {!isGenerating && (
              // General Information
              <div className="alert alert-info mb-4">
                <h6><i className="fas fa-info-circle"></i> Schedule Generation</h6>
                <p className="mb-0">
                  These parameters help create a balanced schedule that's fair to all teams. 
                  Default values work well for a 10-week, 6-teams-per-level case. Adjust them if generation fails or you need different balance requirements.
                </p>
              </div>
            )}
            
            {isGenerating ? (
              <div className="text-center">
                <div className="spinner-border text-primary mb-3" role="status"></div>
                <p>Generating schedule... {elapsedTime}s / {parameters.time_limit}s</p>
                <small className="text-muted">(usually finishes faster)</small>
              </div>
            ) : (
              // Parameter Configuration View
              <div>
                {/* Basic Parameters */}
                <div className="form-section mb-4">
                  <h6 className="form-label">
                    Referee Requirements 
                    <i 
                      className="fas fa-info-circle text-muted ms-2" 
                      style={{ fontSize: '14px', cursor: 'help' }}
                      title="For a 10-week season, each team would ideally referee 5 games. A range of 4-6 games provides good balance while allowing schedule flexibility."
                    ></i>
                  </h6>
                  <div className="row">
                    <div className="col-md-6">
                      <label className="form-label">Minimum Referee Count</label>
                      <input
                        type="number"
                        className="form-control"
                        min="0"
                        value={parameters.min_referee_count}
                        onChange={(e) => handleParameterChange('min_referee_count', e.target.value)}
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">Maximum Referee Count</label>
                      <input
                        type="number"
                        className="form-control"
                        min="0"
                        value={parameters.max_referee_count}
                        onChange={(e) => handleParameterChange('max_referee_count', e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                {/* Slot Limits */}
                <div className="form-section mb-4">
                  <h6 className="form-label">
                    Maximum Games per Team per Time Slot 
                    <i 
                      className="fas fa-info-circle text-muted ms-2" 
                      style={{ fontSize: '14px', cursor: 'help' }}
                      title="These limits prevent teams from playing too many games at the same time each week. Higher numbers give more flexibility but may create uneven schedules. Lower numbers ensure fairness but may make scheduling impossible if too restrictive."
                    ></i>
                  </h6>
                  <div className="row">
                    {Array.from({ length: numSlots }, (_, i) => i + 1).map(slot => (
                      <div key={slot} className="col-md-3 mb-2">
                        <label className="form-label">Slot {slot}</label>
                        <input
                          type="number"
                          className="form-control"
                          min="0"
                          value={parameters.slot_limits[slot] || ''}
                          onChange={(e) => handleSlotLimitChange(slot, e.target.value)}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Time Limit */}
                <div className="form-section mb-4">
                  <h6 className="form-label">
                    Optimization Settings 
                    <i 
                      className="fas fa-info-circle text-muted ms-2" 
                      style={{ fontSize: '14px', cursor: 'help' }}
                      title="Longer times generally produce better schedules but take more time. Start with 60 seconds for most schedules. Increase if you need better balance, decrease if you want faster results."
                    ></i>
                  </h6>
                  <div className="row">
                    <div className="col-md-6">
                      <label className="form-label">Time Limit (seconds)</label>
                      <input
                        type="number"
                        className="form-control"
                        min="1"
                        value={parameters.time_limit}
                        onChange={(e) => handleParameterChange('time_limit', e.target.value)}
                      />
                      <small className="text-muted">Total time to spend optimizing the schedule</small>
                    </div>
                  </div>
                </div>

                {/* Advanced Options Toggle */}
                <div className="mb-3">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                  >
                    {showAdvanced ? 'Hide' : 'Show'} Advanced Options
                  </button>
                </div>

                {/* Advanced Options */}
                {showAdvanced && (
                  <div className="form-section mb-4">
                    <div className="alert alert-warning">
                      <small>
                        <strong>Advanced Options:</strong> These parameters control the internal optimization algorithm. 
                        Only modify if you understand their impact on performance and solution quality.
                      </small>
                    </div>
                    
                    <div className="row">
                      <div className="col-md-6">
                        <label className="form-label">Number of Blueprints</label>
                        <input
                          type="number"
                          className="form-control"
                          min="1"
                          max="100"
                          value={parameters.num_blueprints_to_generate}
                          onChange={(e) => handleParameterChange('num_blueprints_to_generate', e.target.value)}
                        />
                        <small className="text-muted">
                          Fewer blueprints = spend more time optimizing each schedule. 
                          More blueprints = try more variations but less optimization per attempt. Default is 1 blueprint per 10 seconds of the time limit.
                        </small>
                      </div>
                      <div className="col-md-6">
                        <label className="form-label">Relative Gap Tolerance</label>
                        <input
                          type="number"
                          className="form-control"
                          min="0"
                          max="1"
                          step="0.01"
                          value={parameters.gapRel}
                          onChange={(e) => handleParameterChange('gapRel', e.target.value)}
                        />
                        <small className="text-muted">
                          How close to "perfect" the schedule needs to be. Lower values = more optimal but slower. 
                          Higher values = accept slightly less balanced schedules for faster results.
                        </small>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="modal-footer">
            {isGenerating ? (
              <button type="button" className="btn btn-danger" onClick={handleCancel}>
                Cancel Generation
              </button>
            ) : (
              <>
                <button type="button" className="btn btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button type="button" className="btn btn-primary" onClick={handleGenerate}>
                  Generate Schedule
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScheduleParametersModal;