import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import NavBar from './NavBar';
import SeasonList from '../pages/SeasonList';
import OrganizationCreate from '../pages/OrganizationCreate';
import TeamListPage from '../pages/TeamListPage';
import ScheduleCreate from '../pages/ScheduleCreate';
import ScheduleEdit from '../pages/ScheduleEdit';
import ScoreEdit from '../pages/ScoreEdit';
import OrganizationEdit from '../pages/OrganizationEdit';
import PublicSchedule from '../pages/PublicSchedule';

const App = () => {
  return (
    <div className="schedule-app-container">
      <NavBar />
      <div className="content-container">
        <Routes>
          <Route path="/" element={<SeasonList />} />
          <Route path="/teams" element={<TeamListPage />} />
          <Route path="/seasons/create/setup" element={<OrganizationCreate />} />
          <Route path="/seasons/create/schedule" element={<ScheduleCreate />} />
          <Route path="/seasons/:seasonId/edit" element={<ScheduleEdit />} />
          <Route path="/seasons/:seasonId/scores" element={<ScoreEdit />} />
          <Route path="/seasons/:seasonId/structure" element={<OrganizationEdit />} />
          <Route path="/public" element={<PublicSchedule />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;