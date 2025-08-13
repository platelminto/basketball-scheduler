import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import NavBar from './NavBar';
import SeasonList from '../pages/SeasonList';
import TeamSetup from '../pages/TeamSetup';
import ScheduleCreate from '../pages/ScheduleCreate';
import ScheduleEdit from '../pages/ScheduleEdit';
import EditSeasonStructure from '../pages/EditSeasonStructure';
import PublicSchedule from '../pages/PublicSchedule';

const App = () => {
  return (
    <div className="schedule-app-container">
      <NavBar />
      <div className="content-container">
        <Routes>
          <Route path="/" element={<SeasonList />} />
          <Route path="/seasons/create/setup" element={<TeamSetup />} />
          <Route path="/seasons/create/schedule" element={<ScheduleCreate />} />
          <Route path="/seasons/:seasonId/edit" element={<ScheduleEdit />} />
          <Route path="/seasons/:seasonId/structure" element={<EditSeasonStructure />} />
          <Route path="/public" element={<PublicSchedule />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;