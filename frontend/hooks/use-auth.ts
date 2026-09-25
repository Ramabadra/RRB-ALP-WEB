"use client";

import { useEffect, useState } from 'react';
import { User } from '@/types';
import { authApi, usersApi } from '@/lib/api/services';
import { getAccessToken, getStoredUser, clearSession } from '@/lib/auth/token';
import { useRouter } from 'next/navigation';

export function useAuth() {
  const [user, setUser] = useState<User | null>(() => getStoredUser());
  const [loading, setLoading] = useState(() => !getStoredUser() && !!getAccessToken());
  const router = useRouter();

  useEffect(() => {
    let isMounted = true;
    const token = getAccessToken();

    if (!token) {
      Promise.resolve().then(() => {
        if (isMounted) {
          setUser(null);
          setLoading(false);
        }
      });
      return;
    }

    usersApi.getMe()
      .then((me) => {
        if (isMounted) {
          setUser(me);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setUser(null);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const initiateGoogleLogin = async () => {
    try {
      const res = await authApi.getGoogleLoginUrl();
      if (res?.authorization_url) {
        window.location.href = res.authorization_url;
      }
    } catch (err) {
      console.error('Failed to get Google OAuth URL', err);
      throw err;
    }
  };

  const loginWithGoogleToken = async (idToken: string) => {
    const res = await authApi.loginWithGoogleToken(idToken);
    return res;
  };

  const logout = async () => {
    await authApi.logout();
    setUser(null);
    clearSession();
    router.push('/login');
  };

  return {
    user,
    loading,
    isAuthenticated: !!getAccessToken(),
    initiateGoogleLogin,
    loginWithGoogleToken,
    logout,
  };
}
