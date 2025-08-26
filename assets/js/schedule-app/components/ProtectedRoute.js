import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show loading while checking authentication
  if (isLoading) {
    return (
      <div className="page-container">
        <div className="loading-container" style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '50vh'
        }}>
          <div className="spinner"></div>
          <span style={{ marginLeft: '1rem', color: 'var(--text-secondary)' }}>
            Checking authentication...
          </span>
        </div>
      </div>
    );
  }

  // Show 404/access denied if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="page-container">
        <div className="content-container" style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '50vh'
        }}>
          <div className="alert alert-danger" style={{ maxWidth: '400px', textAlign: 'center' }}>
            <h4>Access Denied</h4>
            <p>This page requires authentication.</p>
            <a href="/scheduler/app/scheduler-login" className="btn btn-primary">
              Login
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Render protected content
  return children;
};

export default ProtectedRoute;