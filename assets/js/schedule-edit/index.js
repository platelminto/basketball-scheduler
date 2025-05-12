import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './components/App';
import './styles/schedule-edit.css';

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('schedule-editor');
  if (container) {
    const seasonId = container.dataset.seasonId;
    const root = createRoot(container);
    root.render(<App seasonId={seasonId} />);
  }
});