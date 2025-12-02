/**
 * Centralized API utility with authentication handling
 */

// Cache for CSRF token
let csrfToken = null;

/**
 * Get CSRF token from server
 */
async function getCSRFToken() {
  if (csrfToken) {
    return csrfToken;
  }

  try {
    const response = await fetch('/scheduler/auth/csrf-token/', {
      credentials: 'same-origin'
    });
    const data = await response.json();
    csrfToken = data.csrfToken;
    return csrfToken;
  } catch (error) {
    console.error('Failed to get CSRF token:', error);
    throw error;
  }
}

/**
 * Handle authentication and CSRF errors
 */
function handleAuthError(response) {
  if (response.status === 401) {
    // Clear CSRF token cache on auth error
    csrfToken = null;

    // Redirect to login page
    window.location.href = '/scheduler/auth/login/';
    return true;
  }
  if (response.status === 403) {
    // Clear CSRF token on 403 - likely stale token
    csrfToken = null;
  }
  return false;
}

/**
 * Make authenticated API request
 */
async function apiRequest(url, options = {}, retryOnCsrf = true) {
  const config = {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  };

  // Add CSRF token for non-GET requests
  if (config.method && config.method !== 'GET') {
    try {
      const token = await getCSRFToken();
      config.headers['X-CSRFToken'] = token;
    } catch (error) {
      console.error('Failed to add CSRF token:', error);
      // Continue with request without CSRF token - server will handle it
    }
  }

  try {
    const response = await fetch(url, config);

    // Handle authentication errors
    if (handleAuthError(response)) {
      throw new Error('Authentication required');
    }

    // Handle CSRF errors with automatic retry
    if (response.status === 403 && retryOnCsrf) {
      console.log('CSRF token rejected, refreshing and retrying...');
      csrfToken = null;  // Clear cached token
      return apiRequest(url, options, false);  // Retry once without retry flag
    }

    // Handle other HTTP errors
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    return response;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

/**
 * GET request
 */
export async function apiGet(url) {
  const response = await apiRequest(url, { method: 'GET' });
  return response.json();
}

/**
 * POST request
 */
export async function apiPost(url, data) {
  const response = await apiRequest(url, {
    method: 'POST',
    body: JSON.stringify(data)
  });
  return response.json();
}

/**
 * PUT request
 */
export async function apiPut(url, data) {
  const response = await apiRequest(url, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
  return response.json();
}

/**
 * DELETE request
 */
export async function apiDelete(url, data = null) {
  const config = { method: 'DELETE' };
  if (data) {
    config.body = JSON.stringify(data);
  }
  
  const response = await apiRequest(url, config);
  return response.json();
}

/**
 * Clear CSRF token cache (useful for testing or after logout)
 */
export function clearCSRFToken() {
  csrfToken = null;
}

/**
 * Upload file with authentication
 */
export async function apiUpload(url, formData) {
  try {
    const token = await getCSRFToken();
    
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': token
        // Don't set Content-Type for FormData - browser will set it with boundary
      },
      body: formData
    });

    if (handleAuthError(response)) {
      throw new Error('Authentication required');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('Upload failed:', error);
    throw error;
  }
}

// Export default object with all methods
const api = {
  get: apiGet,
  post: apiPost,
  put: apiPut,
  delete: apiDelete,
  upload: apiUpload,
  clearCSRFToken
};

export default api;