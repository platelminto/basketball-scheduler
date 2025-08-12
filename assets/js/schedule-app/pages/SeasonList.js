import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSchedule } from '../hooks/useSchedule';
import { useStandings } from '../hooks/useStandings';
import StandingsTable from '../components/StandingsTable';
import { SET_SEASON_LIST, SET_LOADING, SET_ERROR } from '../contexts/ScheduleContext';

const SeasonList = () => {
  const { state, dispatch } = useSchedule();
  const navigate = useNavigate();
  const [expandedSeasons, setExpandedSeasons] = useState({});
  const [incompleteWeeksCount, setIncompleteWeeksCount] = useState({});
  const [seasonScheduleData, setSeasonScheduleData] = useState({});
  
  // Function to check for incomplete scores in a season
  const checkIncompleteScores = async (seasonId) => {
    try {
      const response = await fetch(`/scheduler/api/schedule/${seasonId}/`);
      if (!response.ok) return 0;
      
      const data = await response.json();
      if (!data.weeks) return 0;
      
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      
      let incompleteCount = 0;
      
      for (const weekNum in data.weeks) {
        const week = data.weeks[weekNum];
        if (week.isOffWeek || !week.games || week.games.length === 0) continue;
        
        // Check if week date is before today
        const weekDate = new Date(week.monday_date);
        weekDate.setHours(0, 0, 0, 0);
        if (weekDate >= today) continue;
        
        // Count games with both scores
        const gamesWithBothScores = week.games.filter(game => 
          !game.isDeleted && 
          (game.team1_score && game.team1_score !== '') && 
          (game.team2_score && game.team2_score !== '')
        ).length;
        
        const totalActiveGames = week.games.filter(game => !game.isDeleted).length;
        
        // If not all games have complete scores, mark as incomplete
        if (gamesWithBothScores < totalActiveGames) {
          incompleteCount++;
        }
      }
      
      return incompleteCount;
    } catch (error) {
      console.error('Error checking incomplete scores:', error);
      return 0;
    }
  };
  
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
        
        // Check for incomplete scores in active season and fetch its schedule data
        const activeSeason = data.find(season => season.is_active);
        if (activeSeason) {
          const incompleteCount = await checkIncompleteScores(activeSeason.id);
          setIncompleteWeeksCount({ [activeSeason.id]: incompleteCount });
          
          // Fetch schedule data for active season to show standings
          await fetchSeasonSchedule(activeSeason.id);
        }
      } catch (error) {
        console.error('Error fetching seasons:', error);
        dispatch({ type: SET_ERROR, payload: 'Failed to load seasons. Please try again.' });
      }
    };

    fetchSeasons();
  }, [dispatch]);
  
  const fetchSeasonSchedule = async (seasonId) => {
    try {
      const response = await fetch(`/scheduler/api/schedule/${seasonId}/`);
      if (!response.ok) return null;
      
      const data = await response.json();
      setSeasonScheduleData(prev => ({
        ...prev,
        [seasonId]: data
      }));
      return data;
    } catch (error) {
      console.error('Error fetching season schedule:', error);
      return null;
    }
  };

  const toggleExpanded = async (seasonId) => {
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

    // Fetch schedule data when expanding if not already loaded
    if (!seasonScheduleData[seasonId]) {
      await fetchSeasonSchedule(seasonId);
    }
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
      
      // Check for incomplete scores in newly active season
      const activeSeason = data.find(season => season.is_active);
      if (activeSeason) {
        const incompleteCount = await checkIncompleteScores(activeSeason.id);
        setIncompleteWeeksCount({ [activeSeason.id]: incompleteCount });
      }

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
                    {season.name} 
                    {season.is_active && <span className="badge bg-success ms-2">Active</span>}
                    {season.is_active && incompleteWeeksCount[season.id] > 0 && (
                      <span className="badge bg-warning ms-2" title={`${incompleteWeeksCount[season.id]} week(s) with incomplete scores`}>
                        <i className="fas fa-exclamation-triangle"></i> Missing scores
                      </span>
                    )}
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
                  
                  {/* Standings */}
                  {season.levels && season.levels.length > 0 ? (
                    seasonScheduleData[season.id] ? (
                      <SeasonStandings 
                        scheduleData={seasonScheduleData[season.id]}
                        levels={season.levels}
                      />
                    ) : (
                      <div className="d-flex justify-content-center">
                        <div className="spinner-border spinner-border-sm text-primary" role="status">
                          <span className="visually-hidden">Loading standings...</span>
                        </div>
                        <span className="ms-2">Loading standings...</span>
                      </div>
                    )
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
      <Link to="/season/create/team-setup" className="btn btn-primary">
        Create New Season
      </Link>
    </div>
  );
};

const SeasonStandings = ({ scheduleData, levels }) => {
  const standings = useStandings(scheduleData);
  
  if (!standings || standings.length === 0) {
    return (
      <div className="alert alert-info">
        No standings available yet. Games need to be completed to calculate standings.
      </div>
    );
  }
  
  return <StandingsTable standings={standings} levels={levels} showBoth={false} mode="summary" />;
};

export default SeasonList;