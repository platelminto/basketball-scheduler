import React from 'react';
import { createRoot } from 'react-dom/client';
import PublicSchedule from './schedule-app/pages/PublicSchedule';
import './schedule-app/styles/main.css';

// WordPress embed function
window.USBFScheduleEmbed = {
  init: function(containerId = 'usbf-schedule-embed') {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error('USBF Schedule Embed: Container not found with ID:', containerId);
      return;
    }

    // Set explicit white background and padding
    container.style.backgroundColor = '#ffffff';
    container.style.padding = '20px';
    container.style.borderRadius = '8px';

    const root = createRoot(container);
    root.render(<PublicSchedule />);
  }
};

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('usbf-schedule-embed')) {
    window.USBFScheduleEmbed.init();
  }
});