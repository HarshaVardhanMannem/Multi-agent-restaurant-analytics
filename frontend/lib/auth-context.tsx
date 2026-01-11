'use client';

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { User, AuthState, LoginRequest, RegisterRequest, TokenResponse } from '@/types/api';
import { login as apiLogin, register as apiRegister, logout as apiLogout, getStoredUser, getStoredToken, getCurrentUser } from '@/lib/api';

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<TokenResponse>;
  register: (data: RegisterRequest) => Promise<TokenResponse>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Initialize auth state from storage
  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredToken();
      const storedUser = getStoredUser();
      
      if (token && storedUser) {
        // Verify token is still valid
        const user = await getCurrentUser();
        if (user) {
          setState({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
          });
        } else {
          // Token invalid, clear auth
          apiLogout();
          setState({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      } else {
        setState({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    };

    initAuth();
  }, []);

  const login = useCallback(async (credentials: LoginRequest): Promise<TokenResponse> => {
    const response = await apiLogin(credentials);
    setState({
      user: response.user,
      token: response.access_token,
      isAuthenticated: true,
      isLoading: false,
    });
    return response;
  }, []);

  const register = useCallback(async (data: RegisterRequest): Promise<TokenResponse> => {
    const response = await apiRegister(data);
    setState({
      user: response.user,
      token: response.access_token,
      isAuthenticated: true,
      isLoading: false,
    });
    return response;
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  const refreshUser = useCallback(async () => {
    const user = await getCurrentUser();
    if (user) {
      setState(prev => ({ ...prev, user }));
    }
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
