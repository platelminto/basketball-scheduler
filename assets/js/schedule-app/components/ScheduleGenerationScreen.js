import React, { useState, useEffect, useRef } from 'react';

const ScheduleGenerationScreen = ({
  isGenerating,
  elapsedTime,
  parameters,
  progressData,
  onCancel,
  onStopAndUseBest,
  generatedSchedule,
  onApply,
  onClose
}) => {
  const scrollRef = useRef(null);

  // Auto-scroll to bottom when blueprint results update
  useEffect(() => {
    if (scrollRef.current && progressData && progressData.blueprint_results) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [progressData?.blueprint_results]);

  if (isGenerating) {
    return (
      <div className="text-center">
        <div className="spinner-border text-primary mb-3" role="status"></div>
        <p>
          {progressData ? 'Optimizing blueprints' : 'Generating blueprints'}... {elapsedTime}s / {parameters.time_limit}s
        </p>
        
        {/* Explanation of the generation process */}
        <div className="alert alert-info mb-3" style={{ fontSize: '0.9em', textAlign: 'left' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
            <i className="fas fa-info-circle"></i> How Schedule Generation Works
          </div>
          <div style={{ lineHeight: '1.4' }}>
            <strong>Blueprints</strong> are different starting points for schedules, each with random team assignments. 
            The algorithm then optimizes each blueprint to improve balance and fairness.
            <br /><br />
            <strong>Strategy:</strong> It's more effective to try many blueprints for shorter periods than to spend all time on just a few. 
            Starting with a good random foundation often beats heavily optimizing a poor one.
            <br /><br />
            <strong>Infeasible blueprints</strong> mean the constraints are too tight for that particular starting arrangement. 
            Some infeasible results is normal and healthy - it shows the algorithm is exploring the boundaries of what's possible.
          </div>
        </div>
        
        {/* Progress information */}
        {progressData && (
          <div className="mt-3 mb-3">
            <div style={{ fontSize: '0.85em', textAlign: 'left' }}>
              <div className="mb-2" style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>
                {progressData.current_blueprint}/{progressData.total_blueprints} blueprints
                {progressData.best_score !== null && progressData.best_score !== undefined && (
                  <span style={{ marginLeft: '1rem', color: 'var(--success, #10b981)' }}>
                    Best: {typeof progressData.best_score === 'number' ? progressData.best_score.toFixed(2) : progressData.best_score}
                  </span>
                )}
                <span style={{ marginLeft: '1rem', color: 'var(--text-secondary, #6b7280)', fontSize: '0.9em' }}>
                  (Theoretical Best: {progressData.best_possible_score !== null && progressData.best_possible_score !== undefined ? (typeof progressData.best_possible_score === 'number' ? progressData.best_possible_score.toFixed(2) : progressData.best_possible_score) : '...'})
                </span>
              </div>
              
              {/* Blueprint results */}
              {progressData.blueprint_results && Object.keys(progressData.blueprint_results).length > 0 && (
                <div 
                  ref={scrollRef}
                  style={{ 
                    maxHeight: '120px', 
                    overflowY: 'auto',
                    backgroundColor: 'var(--bg-secondary, #f8f9fa)',
                    border: '1px solid var(--border-primary, #e5e7eb)',
                    borderRadius: '4px',
                    padding: '8px'
                  }}
                >
                  {Object.entries(progressData.blueprint_results)
                    .sort(([a], [b]) => parseInt(a) - parseInt(b))
                    .map(([blueprintNum, result]) => {
                      // A blueprint is currently running if it matches current_blueprint AND has no final score yet
                      // BUT if we have scores for all blueprints, then nothing is "currently running"
                      const allBlueprintsHaveResults = Object.keys(progressData.blueprint_results).length === progressData.total_blueprints;
                      const allBlueprintsCompleted = allBlueprintsHaveResults && Object.values(progressData.blueprint_results).every(r => 
                        r.score === 'infeasible' || typeof r.score === 'number'
                      );
                      
                      const isCurrentlyRunning = !allBlueprintsCompleted && 
                                               parseInt(blueprintNum) === progressData.current_blueprint && 
                                               result.score !== 'infeasible' && 
                                               typeof result.score !== 'number';
                      const isBest = result.score !== 'infeasible' && typeof result.score === 'number' && result.score === progressData.best_score;
                      return (
                        <div key={blueprintNum} style={{ 
                          marginBottom: '2px',
                          padding: '2px 6px',
                          backgroundColor: isBest ? 'var(--success-light, #d1fae5)' : 'transparent',
                          borderRadius: '3px',
                          fontSize: '0.9em',
                          lineHeight: '1.3'
                        }}>
                          <span style={{ color: 'var(--text-secondary, #6b7280)' }}>
                            #{blueprintNum}:
                          </span>
                          <span style={{ 
                            marginLeft: '6px',
                            color: result.score === 'infeasible' ? 'var(--warning, #f59e0b)' : 
                                   isCurrentlyRunning ? 'var(--text-secondary, #6b7280)' : 'var(--text-primary)',
                            fontWeight: isBest ? 'bold' : 'normal'
                          }}>
                            {result.score === 'infeasible' ? 'Infeasible' : (isCurrentlyRunning ? 'Running...' : (typeof result.score === 'number' ? result.score.toFixed(2) : result.score))}
                          </span>
                          {isBest && (
                            <span style={{ 
                              marginLeft: '6px',
                              color: 'var(--success, #10b981)',
                              fontWeight: 'bold',
                              fontSize: '0.85em'
                            }}>
                              ← BEST!
                            </span>
                          )}
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-4 d-flex justify-content-end gap-2">
          <button type="button" className="btn btn-danger" onClick={onCancel}>
            Cancel Generation
          </button>
          {progressData && progressData.best_score !== null && progressData.best_score !== undefined && (
            <button 
              type="button" 
              className="btn btn-warning" 
              onClick={onStopAndUseBest}
              title={`Stop generation and use current best schedule (score: ${typeof progressData.best_score === 'number' ? progressData.best_score.toFixed(2) : progressData.best_score})`}
            >
              Stop & Use Best
            </button>
          )}
        </div>
      </div>
    );
  }

  if (generatedSchedule) {
    return (
      <div className="text-center">
        <div className="alert alert-success mb-4">
          <h6><i className="fas fa-check-circle"></i> Schedule Generated Successfully!</h6>
          <p className="mb-0">
            {(() => {
              // Use backend blueprint results if available
              if (progressData && progressData.blueprint_results) {
                const blueprintCount = Object.keys(progressData.blueprint_results).length;
                const hasRunningBlueprints = Object.values(progressData.blueprint_results).some(r => 
                  r.score !== 'infeasible' && typeof r.score !== 'number'
                );
                
                if (hasRunningBlueprints) {
                  return `Stopped early and using best schedule found with ${blueprintCount} blueprint${blueprintCount !== 1 ? 's' : ''} tested.`;
                } else {
                  return `Found an optimal schedule with ${blueprintCount} blueprint${blueprintCount !== 1 ? 's' : ''} tested.`;
                }
              } else {
                return "Schedule generated successfully!";
              }
            })()}
            {(() => {
              // Use backend best score if available
              if (progressData && progressData.best_score !== null && progressData.best_score !== undefined) {
                return (
                  <span style={{ marginLeft: '10px', fontWeight: 'bold' }}>
                    <span style={{ color: 'var(--success, #10b981)' }}>
                      Best Score: {typeof progressData.best_score === 'number' ? progressData.best_score.toFixed(2) : progressData.best_score}
                    </span>
                    {progressData.best_possible_score !== null && progressData.best_possible_score !== undefined && (
                      <span style={{ marginLeft: '8px', color: 'var(--text-secondary, #6b7280)', fontSize: '0.9em', fontWeight: 'normal' }}>
                        (Theoretical Best: {typeof progressData.best_possible_score === 'number' ? progressData.best_possible_score.toFixed(2) : progressData.best_possible_score})
                      </span>
                    )}
                  </span>
                );
              }
              return null;
            })()}
          </p>
        </div>
        
        {/* Final results summary */}
        {progressData && progressData.blueprint_results && Object.keys(progressData.blueprint_results).length > 0 && (
          <div className="mb-4">
            <div style={{ fontSize: '0.85em', textAlign: 'left' }}>
              <div className="mb-2" style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>
                Final Results:
                {progressData && (
                  <span style={{ marginLeft: '1rem', color: 'var(--text-secondary, #6b7280)', fontSize: '0.9em', fontWeight: 'normal' }}>
                    (Theoretical Best: {progressData.best_possible_score !== null && progressData.best_possible_score !== undefined ? (typeof progressData.best_possible_score === 'number' ? progressData.best_possible_score.toFixed(2) : progressData.best_possible_score) : '...'})
                  </span>
                )}
              </div>
              <div 
                style={{ 
                  maxHeight: '120px', 
                  overflowY: 'auto',
                  backgroundColor: 'var(--bg-secondary, #f8f9fa)',
                  border: '1px solid var(--border-primary, #e5e7eb)',
                  borderRadius: '4px',
                  padding: '8px'
                }}
              >
                {Object.entries(progressData.blueprint_results)
                  .sort(([a], [b]) => parseInt(a) - parseInt(b))
                  .map(([blueprintNum, result]) => {
                    const isBest = result.score !== 'infeasible' && typeof result.score === 'number' && result.score === progressData.best_score;
                    return (
                      <div key={blueprintNum} style={{ 
                        marginBottom: '2px',
                        padding: '2px 6px',
                        backgroundColor: isBest ? 'var(--success-light, #d1fae5)' : 'transparent',
                        borderRadius: '3px',
                        fontSize: '0.9em',
                        lineHeight: '1.3'
                      }}>
                        <span style={{ color: 'var(--text-secondary, #6b7280)' }}>
                          #{blueprintNum}:
                        </span>
                        <span style={{ 
                          marginLeft: '6px',
                          color: result.score === 'infeasible' ? 'var(--warning, #f59e0b)' : 'var(--text-primary)',
                          fontWeight: isBest ? 'bold' : 'normal'
                        }}>
                          {result.score === 'infeasible' ? 'Infeasible' : (typeof result.score === 'number' ? result.score.toFixed(2) : result.score)}
                        </span>
                        {isBest && (
                          <span style={{ 
                            marginLeft: '6px',
                            color: 'var(--success, #10b981)',
                            fontWeight: 'bold',
                            fontSize: '0.85em'
                          }}>
                            ← BEST
                          </span>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="d-flex justify-content-center gap-2">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
          <button type="button" className="btn btn-success" onClick={() => {
            // Apply the generated schedule by calling the parent's apply function
            if (onApply && generatedSchedule) {
              onApply({ schedule: generatedSchedule });
            }
            onClose();
          }}>
            Apply Schedule
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default ScheduleGenerationScreen;