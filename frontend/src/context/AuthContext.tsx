import React, { createContext, useContext, useState, useEffect } from 'react';
import type { AuthUser } from '../services/auth';
import {
  getStoredUser,
  getAuthToken,
  loginApi,
  signupApi,
  confirmSignupApi,
  clearAuthSession,
  fetchCurrentUser,
} from '../services/auth';

export type AuthModalTab = 'login' | 'signup' | 'confirm';

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isModalOpen: boolean;
  modalTab: AuthModalTab;
  pendingEmail: string;
  openModal: (tab?: AuthModalTab, email?: string) => void;
  closeModal: () => void;
  setModalTab: (tab: AuthModalTab) => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, role?: 'consumer' | 'pharmacist', name?: string) => Promise<void>;
  confirm: (email: string, code: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(getStoredUser());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [modalTab, setModalTab] = useState<AuthModalTab>('login');
  const [pendingEmail, setPendingEmail] = useState<string>('');

  useEffect(() => {
    const initAuth = async () => {
      const token = getAuthToken();
      if (token) {
        const remoteUser = await fetchCurrentUser();
        if (remoteUser) {
          setUser(remoteUser);
        } else {
          setUser(getStoredUser());
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const openModal = (tab: AuthModalTab = 'login', email: string = '') => {
    setModalTab(tab);
    if (email) setPendingEmail(email);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  const login = async (email: string, password: string) => {
    const tokens = await loginApi(email, password);
    const profile = await fetchCurrentUser();
    const stored = getStoredUser();
    setUser(
      profile ||
        stored || {
          user_id: tokens.user_id || email,
          email: tokens.email || email,
          role: (tokens.role as any) || 'consumer',
          name: tokens.name,
        }
    );
    closeModal();
  };

  const signup = async (
    email: string,
    password: string,
    role: 'consumer' | 'pharmacist' = 'consumer',
    name?: string
  ) => {
    await signupApi(email, password, role, name);
    setPendingEmail(email);
    setModalTab('confirm');
  };

  const confirm = async (email: string, code: string) => {
    await confirmSignupApi(email, code);
    setModalTab('login');
  };

  const logout = () => {
    clearAuthSession();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: Boolean(user && getAuthToken()),
        isLoading,
        isModalOpen,
        modalTab,
        pendingEmail,
        openModal,
        closeModal,
        setModalTab,
        login,
        signup,
        confirm,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
