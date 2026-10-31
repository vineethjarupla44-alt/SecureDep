import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('aicte_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('aicte_access_token'));
  const [loading, setLoading] = useState(true);

  // Synchronize user profile from backend on app load if token exists
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('aicte_access_token');
      if (savedToken) {
        try {
          const res = await api.getCurrentUser();
          if (res?.user) {
            setUser(res.user);
            localStorage.setItem('aicte_user', JSON.stringify(res.user));
          }
        } catch (err) {
          console.warn('Initial session check failed, using cached session or clearing:', err.message);
          // Don't immediately clear if offline; if 401, clear
          if (err.status === 401) {
            api.clearTokens();
            setUser(null);
            setToken(null);
          }
        }
      }
      setLoading(false);
    };

    initAuth();

    const handleExpired = () => {
      setUser(null);
      setToken(null);
    };
    window.addEventListener('aicte_auth_expired', handleExpired);
    return () => window.removeEventListener('aicte_auth_expired', handleExpired);
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const res = await api.login(email, password);
      setUser(res.user);
      setToken(res.access_token);
      return res;
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData) => {
    return await api.register(userData);
  };

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setToken(null);
    }
  };

  // Switch demo persona (for reviewer & local evaluation convenience)
  const switchDemoPersona = async (roleName, customInstitutionId = 1) => {
    const mockPersonas = {
      administrator: {
        id: 1,
        email: 'admin@aicte-india.org',
        full_name: 'AICTE Central Administrator',
        role: 'administrator',
        account_status: 'ACTIVE',
        institution_id: null,
      },
      aicte_official: {
        id: 2,
        email: 'regulator@aicte-india.org',
        full_name: 'AICTE Chief Regulator / Finance Desk',
        role: 'aicte_official',
        account_status: 'ACTIVE',
        institution_id: null,
      },
      institution_user: {
        id: 3,
        email: 'finance@dit.edu.in',
        full_name: 'Delhi Institute of Tech (Finance Desk)',
        role: 'institution_user',
        account_status: 'ACTIVE',
        institution_id: customInstitutionId,
      },
    };

    const targetUser = mockPersonas[roleName] || mockPersonas.administrator;
    setUser(targetUser);
    localStorage.setItem('aicte_user', JSON.stringify(targetUser));
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user && !!token,
    isAdmin: user?.role === 'administrator',
    isOfficial: user?.role === 'aicte_official' || user?.role === 'administrator',
    isInstitutionUser: user?.role === 'institution_user',
    role: user?.role,
    institutionId: user?.institution_id,
    login,
    register,
    logout,
    switchDemoPersona,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};

export default AuthContext;
