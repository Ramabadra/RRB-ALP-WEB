import { User } from '@/types';

// Centralized Token and Session Manager
const TOKEN_KEY = 'rrb_alp_access_token';
const USER_KEY = 'rrb_alp_user';

let memoryToken: string | null = null;
let memoryUser: User | null = null;

export function getAccessToken(): string | null {
  if (memoryToken) return memoryToken;
  if (typeof window !== 'undefined') {
    try {
      const token = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
      if (token) {
        memoryToken = token;
        return token;
      }
    } catch {
      // Storage access may fail in restricted iframes
    }
  }
  return null;
}

export function setAccessToken(token: string): void {
  memoryToken = token;
  if (typeof window !== 'undefined') {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // Ignore storage errors in restricted contexts
    }
  }
}

export function getStoredUser(): User | null {
  if (memoryUser) return memoryUser;
  if (typeof window !== 'undefined') {
    try {
      const raw = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
      if (raw) {
        memoryUser = JSON.parse(raw);
        return memoryUser;
      }
    } catch {
      // Ignore
    }
  }
  return null;
}

export function setStoredUser(user: User | null): void {
  memoryUser = user;
  if (typeof window !== 'undefined') {
    try {
      if (user) {
        sessionStorage.setItem(USER_KEY, JSON.stringify(user));
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      } else {
        sessionStorage.removeItem(USER_KEY);
        localStorage.removeItem(USER_KEY);
      }
    } catch {
      // Ignore
    }
  }
}

export function clearSession(): void {
  memoryToken = null;
  memoryUser = null;
  if (typeof window !== 'undefined') {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(USER_KEY);
      localStorage.removeItem(USER_KEY);
    } catch {
      // Ignore
    }
  }
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
