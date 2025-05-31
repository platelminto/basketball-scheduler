import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import NavBar from './NavBar';
import SeasonList from '../pages/SeasonList';
import TeamSetup from '../pages/TeamSetup';
import ScheduleCreate from '../pages/ScheduleCreate';
import ScheduleEdit from '../pages/ScheduleEdit';
import EditSeasonStructure from '../pages/EditSeasonStructure';

const App = () => {
  return (
    <div className="schedule-app-container">
      <NavBar />
      <div className="content-container">
        <Routes>
          <Route path="/" element={<SeasonList />} />
          <Route path="/seasons" element={<SeasonList />} />
          <Route path="/season/create/team-setup" element={<TeamSetup />} />
          <Route path="/season/create/schedule" element={<ScheduleCreate />} />
          <Route path="/schedule/:seasonId/edit" element={<ScheduleEdit />} />
          <Route path="/edit_season_structure/:seasonId" element={<EditSeasonStructure />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;