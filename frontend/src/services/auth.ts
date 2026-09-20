/**
 * Authentication service for Amazon Cognito API endpoints (§8).
 * Manages JWT tokens, local session persistence, and user profile state.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const TOKEN_KEY = 'medverify_auth_token';
const REFRESH_TOKEN_KEY = 'medverify_refresh_token';
const USER_KEY = 'medverify_auth_user';

export interface AuthUser {
  user_id: string;
  email?: string;
  role: string;
  name?: string;
  email_verified?: boolean;
}

export interface AuthResponse {
  access_token: string;
  id_token?: string;
  refresh_token?: string;
  expires_in?: number;
  token_type?: string;
  role?: string;
  user_id?: string;
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  const data = localStorage.getItem(USER_KEY);
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function saveAuthSession(tokens: AuthResponse, user?: AuthUser) {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  if (tokens.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  }
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

export function clearAuthSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function loginApi(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Login failed. Please check your credentials.');
  }

  const data: AuthResponse = await res.json();
  const user: AuthUser = {
    user_id: data.user_id || email,
    email,
    role: data.role || 'consumer',
  };
  saveAuthSession(data, user);
  return data;
}

export async function signupApi(
  email: string,
  password: string,
  role: 'consumer' | 'pharmacist' = 'consumer',
  name?: string
): Promise<{ status: string; user_id?: string; message: string }> {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, role, name }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Registration failed.');
  }

  return await res.json();
}

export async function confirmSignupApi(email: string, confirmation_code: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/auth/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, confirmation_code }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Confirmation failed. Check your verification code.');
  }

  return await res.json();
}

export async function resendConfirmationApi(email: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/auth/resend-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to resend code.');
  }

  return await res.json();
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      if (res.status === 401) {
        clearAuthSession();
      }
      return null;
    }

    const user: AuthUser = await res.json();
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    return user;
  } catch {
    return getStoredUser();
  }
}
