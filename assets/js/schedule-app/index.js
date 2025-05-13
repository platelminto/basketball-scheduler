import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './components/App';
import { ScheduleProvider } from './contexts/ScheduleContext';
import './styles/main.css';

document.addEventListener('DOMContentLoaded', () => {
  const scheduleAppContainer = document.getElementById('schedule-app');
  if (scheduleAppContainer) {
    const root = createRoot(scheduleAppContainer);
    // Set the basename to '/scheduler/app' so all routes are relative to this path
    root.render(
      <BrowserRouter basename="/scheduler/app">
        <ScheduleProvider>
          <App />
        </ScheduleProvider>
      </BrowserRouter>
    );
  }
});