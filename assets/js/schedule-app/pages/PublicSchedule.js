import React, { useState, useEffect } from 'react';
import MultiSelectDropdown from '../components/MultiSelectDropdown';
import StandingsTable from '../components/StandingsTable';
import ScheduleDisplay from '../components/ScheduleDisplay';
import CalendarExportModal from '../components/CalendarExportModal';
import { useStandings } from '../hooks/useStandings';
import { getFilterOptions } from '../utils/filterUtils';
import { getMostCommonWeekPattern } from '../utils/gameUtils';

const PublicSchedule = () => {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLevels, setSelectedLevels] = useState(['all']);
  const [selectedCourts, setSelectedCourts] = useState(['all']);
  const [selectedReferees, setSelectedReferees] = useState(['all']);
  const [selectedTeams, setSelectedTeams] = useState(['all']);
  const [hidePastGames, setHidePastGames] = useState(false);
  const [viewMode, setViewMode] = useState('both'); // 'both', 'standings', 'schedule'
  const [screenWidth, setScreenWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1400);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [calendarModalOpen, setCalendarModalOpen] = useState(false);

  // Fetch public schedule data
  useEffect(() => {
    const fetchScheduleData = async () => {
      try {
        const response = await fetch('/scheduler/api/public/schedule/');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setScheduleData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchScheduleData();
  }, []);

  // Handle window resize for responsive layout
  useEffect(() => {
    const handleResize = () => setScreenWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Auto-reset to 'both' when screen becomes wide enough
  useEffect(() => {
    if (screenWidth >= 1200 && (viewMode === 'standings' || viewMode === 'schedule')) {
      setViewMode('both');
    }
  }, [screenWidth, viewMode]);

  // Call hooks before any conditional returns
  const filterOptions = getFilterOptions(scheduleData);
  const standings = useStandings(scheduleData);
  const commonWeekTimes = getMostCommonWeekPattern(scheduleData);

  if (loading) {
    return (
      <div className="container mt-4">
        <div className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2">Loading schedule...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mt-4">
        <div className="alert alert-danger">
          <h4>Error loading schedule</h4>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!scheduleData) {
    return (
      <div className="container mt-4">
        <div className="alert alert-warning">
          <h4>No schedule data available</h4>
          <p>There may be no active season or no games scheduled.</p>
        </div>
      </div>
    );
  }


  console.log('Most common week pattern:', commonWeekTimes);
  
  const canShowBoth = screenWidth >= 1200;
  const isMobile = screenWidth < 768;
  const showBoth = canShowBoth && viewMode === 'both';
  const showStandingsOnly = viewMode === 'standings';
  const showScheduleOnly = viewMode === 'schedule' || (!canShowBoth && viewMode === 'both') || (!showStandingsOnly && !showBoth);

  const filters = {
    selectedLevels,
    selectedCourts,
    selectedReferees,
    selectedTeams,
    hidePastGames
  };

  return (
    <div style={{ maxWidth: showBoth ? '1600px' : '1000px', margin: '0 auto', padding: '20px' }}>
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '600', marginBottom: '15px' }}>
          {scheduleData.season.name}
        </h1>
        
        {/* View Toggle - only show if we can't fit both - placed above content */}
        {!canShowBoth && (
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '15px' }}>
            <button
              onClick={() => setViewMode(showStandingsOnly ? 'schedule' : 'standings')}
              style={{
                padding: '6px 12px',
                border: 'none',
                borderRadius: '4px',
                background: '#f5f5f5',
                color: '#333',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                whiteSpace: 'nowrap'
              }}
            >
              <span>{showStandingsOnly ? '📅' : '📊'}</span>
              {showStandingsOnly ? 'Schedule' : 'Standings'}
            </button>
          </div>
        )}
      </div>

      {/* Main Content: Standings and Schedule */}
      <div style={{ 
        display: showBoth ? 'grid' : 'block',
        gridTemplateColumns: showBoth ? '500px 1fr' : 'none',
        gap: showBoth ? '30px' : '0',
        alignItems: 'start'
      }}>
        {(showBoth || showStandingsOnly) && (
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '15px' }}>
              League Standings
            </h2>
            <StandingsTable 
              standings={standings} 
              levels={scheduleData.levels} 
              showBoth={showBoth}
            />
          </div>
        )}

        {(showBoth || showScheduleOnly) && (
          <div>
            {/* Mobile filter toggle button - only above schedule */}
            {isMobile && (
              <button
                onClick={() => setFiltersExpanded(!filtersExpanded)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 12px',
                  marginBottom: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  background: '#f8f9fa',
                  color: '#333',
                  fontSize: '13px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  width: '100%',
                  justifyContent: 'space-between'
                }}
              >
                <span>🔍 Filters</span>
                <span style={{ transform: filtersExpanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s', fontSize: '12px' }}>
                  ▼
                </span>
              </button>
            )}
            
            {/* Filter Controls - only above schedule */}
            <div style={{ 
              display: (isMobile && !filtersExpanded) ? 'none' : 'block',
              marginBottom: '15px'
            }}>
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
                gap: '12px',
                marginBottom: '15px',
                maxWidth: '600px'
              }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
                    Teams
                  </label>
                  <MultiSelectDropdown
                    options={filterOptions.teams.map(team => ({ value: team, label: team }))}
                    selectedValues={selectedTeams}
                    onChange={setSelectedTeams}
                    allLabel="All Teams"
                  />
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
                    Referees
                  </label>
                  <MultiSelectDropdown
                    options={filterOptions.referees.map(ref => ({ value: ref, label: ref }))}
                    selectedValues={selectedReferees}
                    onChange={setSelectedReferees}
                    allLabel="All Referees"
                  />
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
                    Levels
                  </label>
                  <MultiSelectDropdown
                    options={scheduleData.levels.map(level => ({ value: level.id.toString(), label: level.name }))}
                    selectedValues={selectedLevels}
                    onChange={setSelectedLevels}
                    allLabel="All Levels"
                  />
                </div>
                
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#666' }}>
                    Courts
                  </label>
                  <MultiSelectDropdown
                    options={filterOptions.courts.map(court => ({ value: court, label: court }))}
                    selectedValues={selectedCourts}
                    onChange={setSelectedCourts}
                    allLabel="All Courts"
                  />
                </div>
              </div>
            </div>
            
            {/* Action buttons - positioned above schedule */}
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', marginBottom: '15px' }}>
              <button
                onClick={() => setHidePastGames(!hidePastGames)}
                style={{
                  padding: '6px 12px',
                  border: 'none',
                  borderRadius: '4px',
                  background: hidePastGames ? '#333' : '#f5f5f5',
                  color: hidePastGames ? 'white' : '#333',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  whiteSpace: 'nowrap'
                }}
              >
                <span>⏰</span>
                Upcoming Games
              </button>
              
              <button
                onClick={() => setCalendarModalOpen(true)}
                style={{
                  padding: '6px 12px',
                  border: 'none',
                  borderRadius: '4px',
                  background: '#f5f5f5',
                  color: '#333',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  whiteSpace: 'nowrap'
                }}
              >
                <span>📅</span>
                Team Calendars
              </button>
            </div>
            
            <ScheduleDisplay 
              scheduleData={scheduleData} 
              filters={filters}
              commonWeekTimes={commonWeekTimes}
            />
          </div>
        )}
      </div>
      
      {/* Calendar Export Modal */}
      {calendarModalOpen && (
        <CalendarExportModal
          scheduleData={scheduleData}
          onClose={() => setCalendarModalOpen(false)}
        />
      )}
    </div>
  );
};

export default PublicSchedule;