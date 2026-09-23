import { fetchApi } from '../client';
import { User } from '@/types';
import { setStoredUser } from '@/lib/auth/token';

export const usersApi = {
  getMe: async (): Promise<User> => {
    const user = await fetchApi<User>('/api/users/me');
    setStoredUser(user);
    return user;
  },

  updateMe: async (data: Partial<User>): Promise<User> => {
    const user = await fetchApi<User>('/api/users/me', {
      method: 'PATCH',
      body: data,
    });
    setStoredUser(user);
    return user;
  },
};
