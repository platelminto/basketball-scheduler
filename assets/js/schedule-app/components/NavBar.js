import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const NavBar = () => {
  const location = useLocation();
  const { isAuthenticated, user, logout, isLoading } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  // Don't show navbar if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-light">
      <div className="container-fluid">
        <Link className="navbar-brand" to="/">USBF Schedule</Link>
        <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span className="navbar-toggler-icon"></span>
        </button>
        <div className="collapse navbar-collapse" id="navbarNav">
          <ul className="navbar-nav">
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname === '/public' ? 'active' : ''}`}
                to="/public">
                Public Schedule
              </Link>
            </li>
            <li className="nav-item">
              <Link
                className={`nav-link ${(location.pathname === '/seasons' || (location.pathname.includes('/seasons') && !location.pathname.includes('/seasons/create/'))) && !location.pathname.includes('/scores') ? 'active' : ''}`}
                to="/seasons">
                Seasons
              </Link>
            </li>
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname === '/teams' ? 'active' : ''}`}
                to="/teams">
                Teams
              </Link>
            </li>
            <li className="nav-item">
              <a
                className={`nav-link ${location.pathname.includes('/scores') ? 'active' : ''}`}
                href="/scheduler/edit-scores/">
                Update Scores
              </a>
            </li>
          </ul>
          
          <ul className="navbar-nav ms-auto">
            <li className="nav-item">
              <span className="navbar-text" style={{ marginRight: '1rem', color: 'var(--text-secondary)' }}>
                Welcome, {user?.username}
              </span>
            </li>
            <li className="nav-item">
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={handleLogout}
                style={{ marginLeft: '0.5rem' }}
              >
                Logout
              </button>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default NavBar;