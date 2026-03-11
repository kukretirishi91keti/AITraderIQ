/**
 * Authentication service for TraderAI Pro.
 * Handles JWT tokens, login, register, and profile.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'traderai_token';
const USER_KEY = 'traderai_user';

/**
 * Get stored auth token.
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Get stored user data.
 */
export function getUser() {
  try {
    const data = localStorage.getItem(USER_KEY);
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

/**
 * Check if user is authenticated.
 */
export function isAuthenticated() {
  return !!getToken();
}

/**
 * Authenticated fetch wrapper. Adds Bearer token to requests.
 */
export async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    // Token expired or invalid - clear auth state
    logout();
    throw new Error('Session expired. Please login again.');
  }

  return response;
}

/**
 * Register a new user.
 */
export async function register({ email, username, password, fullName, traderStyle }) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      username,
      password,
      full_name: fullName || '',
      trader_style: traderStyle || 'swing',
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Registration failed');
  }

  const data = await response.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  return data;
}

/**
 * Login with username/email and password.
 */
export async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Login failed');
  }

  const data = await response.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  return data;
}

/**
 * Logout - clear stored credentials.
 */
export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Get current user profile from server.
 */
export async function getProfile() {
  const response = await authFetch(`${API_BASE}/api/auth/me`);
  if (!response.ok) throw new Error('Failed to fetch profile');
  return await response.json();
}

/**
 * Update user profile.
 */
export async function updateProfile(updates) {
  const response = await authFetch(`${API_BASE}/api/auth/me`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update profile');
  const data = await response.json();
  localStorage.setItem(USER_KEY, JSON.stringify(data));
  return data;
}

// =============================================================================
// USER DATA (DB-backed watchlist, portfolio, alerts)
// =============================================================================

export async function getUserWatchlist() {
  const response = await authFetch(`${API_BASE}/api/user/watchlist`);
  if (!response.ok) return { watchlist: [] };
  return await response.json();
}

export async function addToWatchlist(symbol, market = 'US') {
  const response = await authFetch(`${API_BASE}/api/user/watchlist`, {
    method: 'POST',
    body: JSON.stringify({ symbol, market }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to add to watchlist');
  }
  return await response.json();
}

export async function removeFromWatchlist(symbol) {
  const response = await authFetch(`${API_BASE}/api/user/watchlist/${symbol}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to remove from watchlist');
  return await response.json();
}

export async function getUserPortfolio() {
  const response = await authFetch(`${API_BASE}/api/user/portfolio`);
  if (!response.ok) return { holdings: [] };
  return await response.json();
}

export async function addToPortfolio({ symbol, shares, avgPrice, currency, market }) {
  const response = await authFetch(`${API_BASE}/api/user/portfolio`, {
    method: 'POST',
    body: JSON.stringify({
      symbol,
      shares,
      avg_price: avgPrice,
      currency: currency || '$',
      market: market || 'US',
    }),
  });
  if (!response.ok) throw new Error('Failed to add to portfolio');
  return await response.json();
}

export async function removeFromPortfolio(itemId) {
  const response = await authFetch(`${API_BASE}/api/user/portfolio/${itemId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to remove from portfolio');
  return await response.json();
}

export async function getUserAlerts() {
  const response = await authFetch(`${API_BASE}/api/user/alerts`);
  if (!response.ok) return { alerts: [] };
  return await response.json();
}

export async function createAlert({ symbol, condition, targetValue }) {
  const response = await authFetch(`${API_BASE}/api/user/alerts`, {
    method: 'POST',
    body: JSON.stringify({
      symbol,
      condition,
      target_value: targetValue,
    }),
  });
  if (!response.ok) throw new Error('Failed to create alert');
  return await response.json();
}

export async function deleteAlert(alertId) {
  const response = await authFetch(`${API_BASE}/api/user/alerts/${alertId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete alert');
  return await response.json();
}

export default {
  getToken, getUser, isAuthenticated,
  register, login, logout,
  getProfile, updateProfile, authFetch,
  getUserWatchlist, addToWatchlist, removeFromWatchlist,
  getUserPortfolio, addToPortfolio, removeFromPortfolio,
  getUserAlerts, createAlert, deleteAlert,
};
