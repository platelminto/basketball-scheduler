import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import NavBar from './NavBar';
import Login from './Login';
import ProtectedRoute from './ProtectedRoute';
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
          {/* Public routes */}
          <Route path="/scheduler-login" element={<Login />} />
          <Route path="/public" element={<PublicSchedule />} />
          
          {/* Default route redirects to seasons */}
          <Route path="/" element={<Navigate to="/seasons" replace />} />
          
          {/* Protected routes */}
          <Route path="/seasons" element={
            <ProtectedRoute>
              <SeasonList />
            </ProtectedRoute>
          } />
          <Route path="/teams" element={
            <ProtectedRoute>
              <TeamListPage />
            </ProtectedRoute>
          } />
          <Route path="/seasons/create/setup" element={
            <ProtectedRoute>
              <OrganizationCreate />
            </ProtectedRoute>
          } />
          <Route path="/seasons/create/schedule" element={
            <ProtectedRoute>
              <ScheduleCreate />
            </ProtectedRoute>
          } />
          <Route path="/seasons/:seasonId/edit" element={
            <ProtectedRoute>
              <ScheduleEdit />
            </ProtectedRoute>
          } />
          <Route path="/seasons/:seasonId/scores" element={
            <ProtectedRoute>
              <ScoreEdit />
            </ProtectedRoute>
          } />
          <Route path="/seasons/:seasonId/structure" element={
            <ProtectedRoute>
              <OrganizationEdit />
            </ProtectedRoute>
          } />
          
          {/* Catch all redirect */}
          <Route path="*" element={<Navigate to="/seasons" replace />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;