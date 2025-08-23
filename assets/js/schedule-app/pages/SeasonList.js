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
      const response = await fetch(`/scheduler/api/seasons/${seasonId}/`);
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
          (game.team1_score !== null && game.team1_score !== undefined && game.team1_score !== '') && 
          (game.team2_score !== null && game.team2_score !== undefined && game.team2_score !== '')
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
      const response = await fetch(`/scheduler/api/seasons/${seasonId}/`);
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
  
  const handleDeleteSeason = async (seasonId, seasonName) => {
    // Show confirmation dialog
    if (!window.confirm(`Are you sure you want to delete the season "${seasonName}"? This action cannot be undone.`)) {
      return;
    }
    
    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

      const response = await fetch(`/scheduler/api/seasons/${seasonId}/delete/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({})
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || `HTTP error! Status: ${response.status}`);
      }

      if (result.success) {
        // Fetch updated seasons list
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
        
        alert(result.message || 'Season deleted successfully');
      } else {
        throw new Error(result.error || 'Failed to delete season');
      }

    } catch (error) {
      console.error('Error deleting season:', error);
      alert(`Failed to delete season: ${error.message}`);
    }
  };
  
  if (state.isLoading) {
    return (
      <div className="page-container">
        <div className="loading-container">
          <div className="spinner" role="status"></div>
          <span>Loading seasons...</span>
        </div>
      </div>
    );
  }
  
  if (state.error) {
    return (
      <div className="page-container">
        <div className="alert alert-danger">
          <h4>Error loading seasons</h4>
          <p>{state.error}</p>
          <button 
            className="btn btn-primary" 
            onClick={() => window.location.reload()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="page-container">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Seasons</h2>
        <Link to="/seasons/create/setup" className="btn btn-primary">
          <i className="fas fa-plus"></i> Create New Season
        </Link>
      </div>

      {state.seasons?.length > 0 ? (
        <div style={{ display: 'grid', gap: '1.5rem', marginBottom: '2rem' }}>
          {state.seasons.map(season => (
            <div 
              key={season.id} 
              className={`card expandable ${season.is_active ? 'active' : ''} ${expandedSeasons[season.id] ? 'expanded' : ''}`}
            >
              <div 
                className={`card-header ${season.is_active ? 'active' : ''}`}
                onClick={() => toggleExpanded(season.id)}
              >
                <div className="card-title">
                  {season.name}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {season.is_active && (
                      <span className="badge badge-success">
                        <i className="fas fa-check-circle"></i> Active
                      </span>
                    )}
                    {season.is_active && incompleteWeeksCount[season.id] > 0 && (
                      <span 
                        className="badge badge-warning" 
                        title={`${incompleteWeeksCount[season.id]} week(s) with incomplete scores`}
                      >
                        <i className="fas fa-exclamation-triangle"></i> Missing scores
                      </span>
                    )}
                    {season.is_complete && (
                      <span 
                        className="badge badge-primary"
                        title="All games completed with scores"
                      >
                        <i className="fas fa-check-double"></i> Complete
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  <span>Created: {new Date(season.created_at).toISOString().split('T')[0]}</span>
                  <i className="fas fa-chevron-down expand-icon"></i>
                </div>
              </div>
              
              <div className="card-content">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    {!season.is_active && (
                      <button 
                        className="btn btn-outline-success"
                        style={{ border: '2px solid var(--success)' }}
                        onClick={() => handleActivateSeason(season.id)}
                      >
                        <i className="fas fa-check-circle"></i> Make Active
                      </button>
                    )}
                    <Link
                      to={`/seasons/${season.id}/scores`}
                      className="btn btn-success"
                    >
                      <i className="fas fa-edit"></i> Update Scores
                    </Link>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <Link
                      to={`/seasons/${season.id}/edit`}
                      className="btn btn-warning"
                    >
                      <i className="fas fa-calendar-alt"></i> Edit Schedule
                    </Link>
                    <Link
                      to={`/seasons/${season.id}/structure`}
                      className="btn btn-info"
                    >
                      <i className="fas fa-users-cog"></i> Edit Organization
                    </Link>
                    {!season.is_active && (
                      <button
                        className="btn btn-danger"
                        onClick={() => handleDeleteSeason(season.id, season.name)}
                      >
                        <i className="fas fa-trash"></i> Delete
                      </button>
                    )}
                  </div>
                </div>
                
                <div style={{ marginTop: '1rem' }}>
                  {season.levels && season.levels.length > 0 ? (
                    seasonScheduleData[season.id] ? (
                      <SeasonStandings 
                        scheduleData={seasonScheduleData[season.id]}
                        levels={season.levels}
                      />
                    ) : (
                      <div className="loading-container">
                        <div className="spinner"></div>
                        <span>Loading standings...</span>
                      </div>
                    )
                  ) : (
                    <div className="alert alert-warning">
                      No levels or teams have been defined for this season yet.
                      <Link to={`/seasons/${season.id}/structure`}> Edit Organization</Link> to add some.
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="alert alert-info" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <h4>No seasons found</h4>
          <p>Create your first season to get started with scheduling games.</p>
        </div>
      )}

    </div>
  );
};

const SeasonStandings = ({ scheduleData, levels }) => {
  const standings = useStandings(scheduleData);
  
  if (!standings || standings.length === 0) {
    return (
      <div className="alert alert-info">
        No teams found for standings.
      </div>
    );
  }
  
  return <StandingsTable standings={standings} levels={levels} showBoth={false} mode="summary" />;
};

export default SeasonList;