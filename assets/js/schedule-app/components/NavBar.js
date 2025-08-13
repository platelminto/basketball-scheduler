import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const NavBar = () => {
  const location = useLocation();

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
                className={`nav-link ${location.pathname === '/' || location.pathname.includes('/seasons') ? 'active' : ''}`}
                to="/">
                Seasons
              </Link>
            </li>
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname.includes('/seasons/create/') ? 'active' : ''}`}
                to="/seasons/create/setup">
                Create Season
              </Link>
            </li>
            <li className="nav-item">
              <Link
                className={`nav-link ${location.pathname === '/public' ? 'active' : ''}`}
                to="/public">
                Public Schedule
              </Link>
            </li>
            <li className="nav-item">
              <a
                className={`nav-link ${location.pathname.includes('/edit') ? 'active' : ''}`}
                href="/scheduler/edit-scores/">
                Edit Scores
              </a>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default NavBar;