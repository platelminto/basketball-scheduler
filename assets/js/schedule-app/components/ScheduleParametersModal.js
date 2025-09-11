import React, { useState, useEffect } from 'react';
import ScheduleGenerationScreen from './ScheduleGenerationScreen';

const ScheduleParametersModal = ({ 
  isOpen, 
  onClose, 
  onGenerate,
  onApply,
  setupData 
}) => {
  // Clean state machine - only one state object
  const [state, setState] = useState({
    mode: 'configure',  // 'configure' | 'generating' | 'results'
    parameters: {
      time_limit: 180,
      num_blueprints_to_generate: '',
      gapRel: 0.07
    },
    showAdvanced: false,
    generationData: null,  // { schedule, progressData, elapsedTime }
    abortController: null
  });

  // Reset when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setState({
        mode: 'configure',
        parameters: {
          time_limit: 180,
          num_blueprints_to_generate: '',
          gapRel: 0.07
        },
        showAdvanced: false,
        generationData: null,
        abortController: null
      });
    }
  }, [isOpen]);

  // Progress polling - simple and clean
  useEffect(() => {
    if (state.mode !== 'generating') return;

    const pollProgress = async () => {
      try {
        const response = await fetch('/scheduler/api/seasons/generation-progress/', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.progress) {
            setState(prev => ({
              ...prev,
              generationData: {
                ...prev.generationData,
                progressData: data.progress
              }
            }));
          }
        }
      } catch (error) {
        // Ignore polling errors
      }
    };

    // Start polling immediately, then every 2 seconds
    pollProgress();
    const interval = setInterval(pollProgress, 2000);
    
    return () => clearInterval(interval);
  }, [state.mode]);

  // Time counter
  useEffect(() => {
    if (state.mode !== 'generating') return;

    const interval = setInterval(() => {
      setState(prev => ({
        ...prev,
        generationData: {
          ...prev.generationData,
          elapsedTime: (prev.generationData?.elapsedTime || 0) + 1
        }
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, [state.mode]);

  // Helper function to get CSRF token
  const getCsrfToken = () => {
    return document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';
  };

  const handleParameterChange = (key, value) => {
    setState(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        [key]: value === '' ? '' : (key === 'gapRel' ? parseFloat(value) : parseInt(value))
      }
    }));
  };

  const handleGenerate = async () => {
    // Validate all fields are filled
    const emptyFields = [];
    
    if (state.parameters.time_limit === '') emptyFields.push('Time Limit');
    if (state.parameters.gapRel === '') emptyFields.push('Relative Gap Tolerance');
    
    if (emptyFields.length > 0) {
      alert(`Please fill in all fields:\n• ${emptyFields.join('\n• ')}`);
      return;
    }
    
    // Create abort controller and start generation
    const controller = new AbortController();
    
    setState(prev => ({
      ...prev,
      mode: 'generating',
      abortController: controller,
      generationData: {
        schedule: null,
        progressData: null,
        elapsedTime: 0
      }
    }));
    
    try {
      const result = await onGenerate(state.parameters, controller.signal);
      
      // Only proceed if not cancelled
      if (!controller.signal.aborted) {
        // Success - transition to results
        setState(prev => ({
          ...prev,
          mode: 'results',
          abortController: null,
          generationData: {
            ...prev.generationData,
            schedule: result.schedule,
            // Update progressData with final blueprint_results if provided
            progressData: result.blueprint_results ? {
              ...prev.generationData?.progressData,
              blueprint_results: result.blueprint_results
            } : prev.generationData?.progressData
          }
        }));
      }
    } catch (error) {
      // Only reset if this isn't an expected abort (from cancel or stop & use best)
      if (!controller.signal.aborted) {
        // Actual error - go back to configure
        setState(prev => ({
          ...prev,
          mode: 'configure',
          abortController: null,
          generationData: null
        }));
      }
      // If aborted, we don't touch state - it was set by cancel/stop handlers
    }
  };

  const handleCancel = async () => {
    // Cancel backend generation
    try {
      await fetch('/scheduler/api/seasons/cancel-generation/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({})
      });
    } catch (error) {
      // Ignore cancellation errors
    }

    // Abort frontend request and go back to configure
    if (state.abortController) {
      state.abortController.abort();
    }
    
    setState(prev => ({
      ...prev,
      mode: 'configure',
      abortController: null,
      generationData: null
    }));
  };

  const handleStopAndUseBest = async () => {
    const progressData = state.generationData?.progressData;
    
    if (!progressData || progressData.best_score === null || progressData.best_score === undefined) {
      alert('No best schedule available yet. Try generating for longer before stopping.');
      return;
    }

    // Get the latest progress to ensure we have the best schedule
    let latestProgressData = progressData;
    try {
      const response = await fetch('/scheduler/api/seasons/generation-progress/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.progress && data.progress.best_schedule) {
          latestProgressData = data.progress;
        }
      }
    } catch (error) {
      console.warn('Could not fetch latest progress, using current data:', error);
    }
    
    const bestSchedule = latestProgressData.best_schedule;
    
    if (!bestSchedule) {
      alert('No best schedule available yet. Try generating for longer before stopping.');
      return;
    }

    // Cancel backend generation
    try {
      await fetch('/scheduler/api/seasons/cancel-generation/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({})
      });
    } catch (error) {
      // Ignore cancellation errors
    }

    // Abort frontend request and transition to results with best schedule
    if (state.abortController) {
      state.abortController.abort();
    }
    
    setState(prev => ({
      ...prev,
      mode: 'results',
      abortController: null,
      generationData: {
        ...prev.generationData,
        schedule: bestSchedule,
        progressData: latestProgressData
      }
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="modal" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Schedule Generation Parameters</h5>
            {state.mode === 'configure' && (
              <button 
                type="button" 
                className="btn-close" 
                onClick={onClose}
                aria-label="Close"
              ></button>
            )}
          </div>

          <div className="modal-body">
            {state.mode === 'configure' && (
              <>
                {/* Info banner */}
                <div className="alert alert-info mb-4">
                  <h6><i className="fas fa-info-circle"></i> Schedule Generation</h6>
                  <p className="mb-0">
                    Configure the optimization settings for schedule generation. 
                    The generator automatically balances referee assignments and time slot distribution.
                  </p>
                </div>
                
                {/* Time Limit */}
                <div className="form-section mb-4">
                  <h6 className="form-label">
                    Optimization Settings 
                    <i 
                      className="fas fa-info-circle text-muted ms-2" 
                      style={{ fontSize: '14px', cursor: 'help' }}
                      title="Longer times generally produce better schedules but take more time. Start with 300 seconds for most schedules."
                    ></i>
                  </h6>
                  <div className="row">
                    <div className="col-md-6">
                      <label className="form-label">Time Limit (seconds)</label>
                      <input
                        type="number"
                        className="form-control"
                        min="1"
                        value={state.parameters.time_limit}
                        onChange={(e) => handleParameterChange('time_limit', e.target.value)}
                      />
                      <small className="text-muted">Total time to spend optimizing the schedule.</small>
                    </div>
                  </div>
                </div>

                {/* Advanced Options Toggle */}
                <div className="mb-3">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setState(prev => ({ ...prev, showAdvanced: !prev.showAdvanced }))}
                  >
                    {state.showAdvanced ? 'Hide' : 'Show'} Advanced Options
                  </button>
                </div>

                {/* Advanced Options */}
                {state.showAdvanced && (
                  <div className="form-section mb-4">
                    <div className="alert alert-warning">
                      <small>
                        <strong>Advanced Options:</strong> These parameters control the internal optimization algorithm.
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
                          value={state.parameters.num_blueprints_to_generate}
                          onChange={(e) => handleParameterChange('num_blueprints_to_generate', e.target.value)}
                        />
                        <small className="text-muted">
                          Leave empty for automatic. Default is 1 blueprint per 6 seconds.
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
                          value={state.parameters.gapRel}
                          onChange={(e) => handleParameterChange('gapRel', e.target.value)}
                        />
                        <small className="text-muted">
                          How close to "perfect" the schedule needs to be. Lower = more optimal but slower.
                        </small>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {(state.mode === 'generating' || state.mode === 'results') && (
              <ScheduleGenerationScreen
                isGenerating={state.mode === 'generating'}
                elapsedTime={state.generationData?.elapsedTime || 0}
                parameters={state.parameters}
                progressData={state.generationData?.progressData}
                onCancel={handleCancel}
                onStopAndUseBest={handleStopAndUseBest}
                generatedSchedule={state.generationData?.schedule}
                onApply={onApply}
                onClose={onClose}
              />
            )}
          </div>

          {/* Footer only for configure mode */}
          {state.mode === 'configure' && (
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={handleGenerate}>
                Generate Schedule
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScheduleParametersModal;