import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import NavBar from './NavBar';
import SeasonList from '../pages/SeasonList';
import ScheduleCreate from '../pages/ScheduleCreate';
import TeamSetup from '../pages/TeamSetup';
import GameAssignment from '../pages/GameAssignment';
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
          <Route path="/schedule/create" element={<ScheduleCreate />} />
          <Route path="/team_setup" element={<TeamSetup />} />
          <Route path="/game_assignment" element={<GameAssignment />} />
          <Route path="/schedule/:seasonId/edit" element={<ScheduleEdit />} />
          <Route path="/edit_season_structure/:seasonId" element={<EditSeasonStructure />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;