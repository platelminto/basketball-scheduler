import React, { useState } from 'react';

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
    num_blueprints_to_generate: 6,
    gapRel: 0.25
  });

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState('');

  const handleParameterChange = (key, value) => {
    setParameters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSlotLimitChange = (slot, value) => {
    setParameters(prev => ({
      ...prev,
      slot_limits: {
        ...prev.slot_limits,
        [slot]: parseInt(value) || 0
      }
    }));
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setProgress(0);
    setProgressText('Initializing schedule generation...');
    
    // Start the fake progress bar
    const timeLimit = parameters.time_limit * 1000; // Convert to milliseconds
    const updateInterval = 100; // Update every 100ms
    const totalSteps = timeLimit / updateInterval;
    let currentStep = 0;
    
    const progressMessages = [
      'Initializing schedule generation...',
      'Generating matchup blueprints...',
      'Optimizing time slot assignments...',
      'Assigning referees...',
      'Balancing slot distributions...',
      'Running final optimizations...',
      'Finalizing schedule...'
    ];
    
    const progressInterval = setInterval(() => {
      currentStep++;
      const newProgress = Math.min((currentStep / totalSteps) * 100, 95); // Cap at 95% until actual completion
      setProgress(newProgress);
      
      // Update message based on progress
      const messageIndex = Math.floor((newProgress / 100) * (progressMessages.length - 1));
      setProgressText(progressMessages[messageIndex] || progressMessages[0]);
    }, updateInterval);
    
    try {
      await onGenerate(parameters);
      // Complete the progress bar
      clearInterval(progressInterval);
      setProgress(100);
      setProgressText('Schedule generated successfully!');
      
      // Close modal after a brief delay to show completion
      setTimeout(() => {
        setIsGenerating(false);
        setProgress(0);
        setProgressText('');
        onClose();
      }, 1000);
    } catch (error) {
      clearInterval(progressInterval);
      setProgress(0);
      setProgressText('');
      setIsGenerating(false);
      // Error handling is done by the parent component
    }
  };

  const handleCancel = () => {
    if (isGenerating) {
      // TODO: Add actual cancellation logic when threading is implemented
      setIsGenerating(false);
      setProgress(0);
      setProgressText('');
    }
    onClose();
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
            <button 
              type="button" 
              className="btn-close" 
              onClick={onClose}
              aria-label="Close"
            ></button>
          </div>

          <div className="modal-body">
            {!isGenerating && (
              // General Information
              <div className="alert alert-info mb-4">
                <h6><i className="fas fa-info-circle"></i> Schedule Generation Balance</h6>
                <p className="mb-0">
                  In a perfect world, every team would play the exact same number of games in each time slot. 
                  However, creating a real schedule requires compromises. These parameters help balance fairness 
                  with practicality - but setting them too strictly may cause generation to fail or take much longer.
                </p>
              </div>
            )}
            
            {isGenerating ? (
              // Progress Bar View
              <div className="text-center">
                <h6 className="mb-4">Generating Schedule...</h6>
                <div className="progress mb-3" style={{ height: '20px' }}>
                  <div 
                    className="progress-bar progress-bar-striped progress-bar-animated" 
                    role="progressbar" 
                    style={{ width: `${progress}%` }}
                    aria-valuenow={progress} 
                    aria-valuemin="0" 
                    aria-valuemax="100"
                  >
                    {Math.round(progress)}%
                  </div>
                </div>
                <p className="text-muted">{progressText}</p>
                <div className="mt-3">
                  <small className="text-muted">
                    Estimated time: {parameters.time_limit} seconds
                  </small>
                </div>
              </div>
            ) : (
              // Parameter Configuration View
              <div>
                {/* Basic Parameters */}
                <div className="form-section mb-4">
                  <h6 className="form-label">Referee Requirements</h6>
                  <div className="alert alert-light border-left-info mb-3">
                    <small>
                      <strong>Fair distribution:</strong> For a 10-week season, each team would ideally referee 5 games. 
                      A range of 4-6 games provides good balance while allowing schedule flexibility.
                    </small>
                  </div>
                  <div className="row">
                    <div className="col-md-6">
                      <label className="form-label">Minimum Referee Count</label>
                      <input
                        type="number"
                        className="form-control"
                        min="0"
                        value={parameters.min_referee_count}
                        onChange={(e) => handleParameterChange('min_referee_count', parseInt(e.target.value) || 0)}
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">Maximum Referee Count</label>
                      <input
                        type="number"
                        className="form-control"
                        min="0"
                        value={parameters.max_referee_count}
                        onChange={(e) => handleParameterChange('max_referee_count', parseInt(e.target.value) || 0)}
                      />
                    </div>
                  </div>
                </div>

                {/* Slot Limits */}
                <div className="form-section mb-4">
                  <h6 className="form-label">Maximum Games per Team per Time Slot</h6>
                  <div className="alert alert-light border-left-warning mb-3">
                    <small>
                      <strong>Time slot balance:</strong> These limits prevent teams from playing too many games 
                      at the same time each week. Higher numbers give more flexibility but may create uneven schedules. 
                      Lower numbers ensure fairness but may make scheduling impossible if too restrictive.
                    </small>
                  </div>
                  <div className="row">
                    {Array.from({ length: numSlots }, (_, i) => i + 1).map(slot => (
                      <div key={slot} className="col-md-3 mb-2">
                        <label className="form-label">Slot {slot}</label>
                        <input
                          type="number"
                          className="form-control"
                          min="0"
                          value={parameters.slot_limits[slot] || 0}
                          onChange={(e) => handleSlotLimitChange(slot, e.target.value)}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Time Limit */}
                <div className="form-section mb-4">
                  <h6 className="form-label">Optimization Settings</h6>
                  <div className="alert alert-light border-left-success mb-3">
                    <small>
                      <strong>Optimization time:</strong> Longer times generally produce better schedules but take more time. 
                      Start with 60 seconds for most schedules. Increase if you need better balance, decrease if you want faster results.
                    </small>
                  </div>
                  <div className="row">
                    <div className="col-md-6">
                      <label className="form-label">Time Limit (seconds)</label>
                      <input
                        type="number"
                        className="form-control"
                        min="1"
                        value={parameters.time_limit}
                        onChange={(e) => handleParameterChange('time_limit', parseInt(e.target.value) || 60)}
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
                          onChange={(e) => handleParameterChange('num_blueprints_to_generate', parseInt(e.target.value) || 6)}
                        />
                        <small className="text-muted">
                          Fewer blueprints = spend more time optimizing each schedule. 
                          More blueprints = try more variations but less optimization per attempt.
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
                          onChange={(e) => handleParameterChange('gapRel', parseFloat(e.target.value) || 0.25)}
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