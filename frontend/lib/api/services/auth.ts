import { fetchApi } from '../client';
import { AuthResponse, GoogleLoginUrlResponse, User } from '@/types';
import { setAccessToken, setStoredUser, clearSession } from '@/lib/auth/token';

export const authApi = {
  // Exchange Google ID token for backend JWT
  loginWithGoogleToken: async (googleToken: string): Promise<AuthResponse> => {
    const res = await fetchApi<AuthResponse>('/api/auth/google', {
      method: 'POST',
      body: { token: googleToken },
      skipAuth: true,
    });
    if (res?.token) {
      setAccessToken(res.token);
    }
    if (res?.user) {
      setStoredUser(res.user);
    }
    return res;
  },

  // Get backend Google OAuth authorization redirect URL
  getGoogleLoginUrl: async (): Promise<GoogleLoginUrlResponse> => {
    return fetchApi<GoogleLoginUrlResponse>('/api/auth/google/login', {
      method: 'GET',
      skipAuth: true,
    });
  },

  // Handle OAuth callback
  handleGoogleCallback: async (code: string, state?: string): Promise<AuthResponse> => {
    const res = await fetchApi<AuthResponse>('/api/auth/google/callback', {
      method: 'GET',
      params: { code, state },
      skipAuth: true,
    });
    if (res?.token) {
      setAccessToken(res.token);
    }
    if (res?.user) {
      setStoredUser(res.user);
    }
    return res;
  },

  // Logout
  logout: async (): Promise<void> => {
    try {
      await fetchApi<void>('/api/auth/logout', {
        method: 'POST',
      });
    } catch {
      // Proceed with local cleanup regardless of backend error
    } finally {
      clearSession();
    }
  },
};
