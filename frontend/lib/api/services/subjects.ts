import { fetchApi, USE_MOCKS } from '../client';
import { Subject } from '@/types';
import { mockSubjects } from '../mock-services';

export const subjectsApi = {
  getSubjects: async (): Promise<Subject[]> => {
    if (USE_MOCKS) {
      return mockSubjects;
    }
    try {
      const data = await fetchApi<Subject[]>('/api/subjects');
      return Array.isArray(data) ? data : [];
    } catch (err) {
      if (USE_MOCKS) return mockSubjects;
      throw err;
    }
  },

  getById: async (id: string): Promise<Subject> => {
    return fetchApi<Subject>(`/api/subjects/${id}`);
  },
};
