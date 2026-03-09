/**
 * AuthContext - Manages authentication state across the app.
 */
import React, { createContext, useContext, useState, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, logout as apiLogout, getUser, isAuthenticated, getToken } from '../services/auth';

const AuthContext = createContext(undefined);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(getUser);
  const [isLoggedIn, setIsLoggedIn] = useState(isAuthenticated);
  const [showAuthModal, setShowAuthModal] = useState(false);

  const login = useCallback(async (username, password) => {
    const data = await apiLogin(username, password);
    setUser(data.user);
    setIsLoggedIn(true);
    setShowAuthModal(false);
    return data;
  }, []);

  const register = useCallback(async (formData) => {
    const data = await apiRegister(formData);
    setUser(data.user);
    setIsLoggedIn(true);
    setShowAuthModal(false);
    return data;
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
    setIsLoggedIn(false);
  }, []);

  const value = {
    user, isLoggedIn, showAuthModal,
    login, register, logout,
    setShowAuthModal,
    token: getToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export default AuthContext;
