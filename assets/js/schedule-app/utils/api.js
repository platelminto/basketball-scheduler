/**
 * Centralized API utility with authentication handling
 */

/**
 * Get CSRF token from cookie (always fresh, no caching issues)
 */
function getCSRFToken() {
  const value = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return value || null;
}

/**
 * Handle authentication errors
 */
function handleAuthError(response) {
  if (response.status === 401) {
    window.location.href = '/scheduler/auth/login/';
    return true;
  }
  return false;
}

/**
 * Make authenticated API request
 */
async function apiRequest(url, options = {}) {
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
    const token = getCSRFToken();
    if (token) {
      config.headers['X-CSRFToken'] = token;
    }
  }

  try {
    const response = await fetch(url, config);

    // Handle authentication errors
    if (handleAuthError(response)) {
      throw new Error('Authentication required');
    }

    // Handle HTTP errors
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
 * Upload file with authentication
 */
export async function apiUpload(url, formData) {
  try {
    const token = getCSRFToken();

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
  upload: apiUpload
};

export default api;