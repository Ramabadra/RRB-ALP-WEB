import { fetchApi, USE_MOCKS } from '../client';
import { Topic } from '@/types';
import { mockTopics } from '../mock-services';

export const topicsApi = {
  getTopics: async (subjectId?: string): Promise<Topic[]> => {
    if (USE_MOCKS) {
      return subjectId ? mockTopics.filter(t => t.subjectId === subjectId) : mockTopics;
    }
    try {
      const data = await fetchApi<Topic[]>('/api/topics', {
        params: subjectId ? { subjectId, subject_id: subjectId } : undefined,
      });
      return Array.isArray(data) ? data : [];
    } catch (err) {
      if (USE_MOCKS) return mockTopics;
      throw err;
    }
  },

  getById: async (id: string): Promise<Topic> => {
    return fetchApi<Topic>(`/api/topics/${id}`);
  },
};
