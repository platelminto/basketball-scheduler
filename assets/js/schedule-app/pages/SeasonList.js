import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { SET_SEASON_LIST, SET_LOADING, SET_ERROR } from '../contexts/ScheduleContext';

const SeasonList = () => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const [expandedSeasons, setExpandedSeasons] = useState({});
  
  useEffect(() => {
    const fetchSeasons = async () => {
      dispatch({ type: SET_LOADING, payload: true });

      try {
        const response = await fetch('/scheduler/api/seasons/');

        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Fetched seasons data:', data); // For debugging
        dispatch({ type: SET_SEASON_LIST, payload: data });

        // Initialize expanded states based on active season
        const expandedStates = {};
        data.forEach(season => {
          expandedStates[season.id] = season.is_active;
        });
        setExpandedSeasons(expandedStates);
      } catch (error) {
        console.error('Error fetching seasons:', error);
        dispatch({ type: SET_ERROR, payload: 'Failed to load seasons. Please try again.' });
      }
    };

    fetchSeasons();
  }, [dispatch]);
  
  const toggleExpanded = (seasonId) => {
    setExpandedSeasons(prev => {
      // If this season was already expanded and is being clicked again, collapse it
      if (prev[seasonId]) {
        return {
          ...prev,
          [seasonId]: false
        };
      }

      // Otherwise, collapse all seasons and expand only this one
      const allCollapsed = {};
      Object.keys(prev).forEach(id => {
        allCollapsed[id] = false;
      });

      return {
        ...allCollapsed,
        [seasonId]: true
      };
    });
  };
  
  const handleActivateSeason = async (seasonId) => {
    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

      const response = await fetch(`/scheduler/api/seasons/${seasonId}/activate/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        // Add an empty body to ensure it's treated as JSON
        body: JSON.stringify({})
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      // Fetch updated seasons list instead of reloading the page
      const updatedResponse = await fetch('/scheduler/api/seasons/');
      if (!updatedResponse.ok) {
        throw new Error('Failed to refresh seasons list');
      }

      const data = await updatedResponse.json();
      dispatch({ type: SET_SEASON_LIST, payload: data });

      // Update expanded states
      const expandedStates = {};
      data.forEach(season => {
        expandedStates[season.id] = season.is_active;
      });
      setExpandedSeasons(expandedStates);

    } catch (error) {
      console.error('Error activating season:', error);
      alert('Failed to activate season. Please try again.');
    }
  };
  
  if (state.isLoading) {
    return (
      <div className="container mt-4">
        <div className="d-flex justify-content-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    );
  }
  
  if (state.error) {
    return (
      <div className="container mt-4">
        <div className="alert alert-danger" role="alert">
          {state.error}
          <button 
            className="btn btn-outline-primary ms-3" 
            onClick={() => window.location.reload()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mt-4">
      <h2>Seasons</h2>

      {state.seasons?.length > 0 ? (
        <div className="accordion" id="seasonsAccordion">
          {state.seasons.map(season => (
            <div 
              key={season.id} 
              className={`accordion-item mb-2 ${season.is_active ? 'border border-success' : ''}`}
            >
              <h2 className="accordion-header" id={`heading${season.id}`}>
                <button 
                  className={`accordion-button ${!expandedSeasons[season.id] ? 'collapsed' : ''} ${season.is_active ? 'bg-success-light' : ''}`} 
                  type="button" 
                  onClick={() => toggleExpanded(season.id)}
                  aria-expanded={expandedSeasons[season.id] ? 'true' : 'false'} 
                  aria-controls={`collapse${season.id}`}
                >
                  <span className="me-auto">
                    {season.name} {season.is_active && <span className="badge bg-success ms-2">Active</span>}
                  </span>
                  <small className="text-muted">
                    Created: {new Date(season.created_at).toISOString().split('T')[0]}
                  </small>
                </button>
              </h2>
              <div 
                id={`collapse${season.id}`} 
                className={`accordion-collapse collapse ${expandedSeasons[season.id] ? 'show' : ''}`} 
                aria-labelledby={`heading${season.id}`}
              >
                <div className="accordion-body">
                  {/* Action Buttons */}
                  <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
                    <div>
                      {!season.is_active ? (
                        <button 
                          className="btn btn-sm btn-success"
                          onClick={() => handleActivateSeason(season.id)}
                        >
                          <i className="fas fa-check-circle me-1"></i> Make Active
                        </button>
                      ) : (
                        <span className="badge bg-success p-2">
                          <i className="fas fa-check-circle me-1"></i> Currently Active
                        </span>
                      )}
                    </div>
                    
                    <div className="d-flex gap-2">
                      <Link
                        to={`/schedule/${season.id}/edit`}
                        className="btn btn-sm btn-warning"
                      >
                        <i className="fas fa-calendar-alt me-1"></i> Edit Schedule/Scores
                      </Link>
                      <Link
                        to={`/edit_season_structure/${season.id}`}
                        className="btn btn-sm btn-info"
                      >
                        <i className="fas fa-users-cog me-1"></i> Edit Teams/Levels
                      </Link>
                    </div>
                  </div>
                  
                  {/* Levels and Teams */}
                  {season.levels && season.levels.length > 0 ? (
                    <>
                      <h6>Levels and Teams</h6>
                      <div className="row">
                        {season.levels.map(level => (
                          <div key={level.id} className="col-md-6 col-lg-4 mb-3">
                            <div className="card shadow-sm">
                              <div className="card-header bg-light">
                                <strong>{level.name}</strong>
                              </div>
                              <ul className="list-group list-group-flush">
                                {level.teams && level.teams.length > 0 ? 
                                  level.teams.map(team => (
                                    <li key={team.id} className="list-group-item">{team.name}</li>
                                  )) : 
                                  <li className="list-group-item text-muted fst-italic">No teams in this level.</li>
                                }
                              </ul>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="alert alert-light border" role="alert">
                      No levels or teams have been defined for this season yet.
                      <Link
                        to={`/edit_season_structure/${season.id}`}
                        className="alert-link"
                      > Edit Teams/Levels</Link> to add some.
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="alert alert-info">No seasons found.</p>
      )}

      <hr />
      <Link to="/schedule/create" className="btn btn-primary">
        Create New Season
      </Link>
    </div>
  );
};

export default SeasonList;