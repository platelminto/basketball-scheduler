import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';

const Login = () => {
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { login, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = location.state?.from?.pathname || '/seasons';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (error) {
      clearError();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!credentials.username.trim() || !credentials.password) {
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await login(credentials.username, credentials.password);
      
      if (result.success) {
        // Navigation will be handled by useEffect when isAuthenticated changes
        const from = location.state?.from?.pathname || '/seasons';
        navigate(from, { replace: true });
      }
    } catch (error) {
      console.error('Login submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-container">
      <div className="content-container" style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '60vh' 
      }}>
        <div className="card" style={{ width: '100%', maxWidth: '400px' }}>
          <div className="card-header">
            <h2 className="card-title">Login</h2>
            <p style={{ 
              margin: '0.5rem 0 0 0', 
              color: 'var(--text-secondary)', 
              fontSize: '0.9rem' 
            }}>
              Please sign in to access the schedule manager
            </p>
          </div>
          
          <div className="card-content">
            <form onSubmit={handleSubmit}>
              <div className="form-section">
                <label htmlFor="username" className="form-label">
                  Username
                </label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  className="form-control"
                  value={credentials.username}
                  onChange={handleInputChange}
                  required
                  disabled={isSubmitting}
                  autoComplete="username"
                  autoFocus
                />
              </div>
              
              <div className="form-section">
                <label htmlFor="password" className="form-label">
                  Password
                </label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  className="form-control"
                  value={credentials.password}
                  onChange={handleInputChange}
                  required
                  disabled={isSubmitting}
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <div className="alert alert-danger" style={{ margin: '1rem 0' }}>
                  {error}
                </div>
              )}
              
              <button
                type="submit"
                className={`btn btn-primary ${isSubmitting ? 'loading' : ''}`}
                disabled={isSubmitting || !credentials.username.trim() || !credentials.password}
                style={{ width: '100%', marginTop: '1rem' }}
              >
                {isSubmitting ? 'Signing In...' : 'Sign In'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;