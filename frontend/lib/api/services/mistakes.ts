import { fetchApi, USE_MOCKS } from '../client';
import { MistakeQuestion } from '@/types';
import { mockQuestions } from '../mock-services';

export const mistakesApi = {
  list: async (subjectId?: string, page = 1): Promise<MistakeQuestion[]> => {
    if (USE_MOCKS) {
      return mockQuestions.slice(0, 5).map((q, i) => ({
        id: `mis-${i + 1}`,
        questionId: q.id,
        attemptId: 'att-1',
        savedAt: new Date().toISOString(),
        userAnswerId: 'opt-2',
        question: q,
      }));
    }

    try {
      const data = await fetchApi<any>('/api/mistakes', {
        params: {
          subjectId,
          subject_id: subjectId,
          page,
        },
      });

      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
    } catch (err) {
      if (USE_MOCKS) {
        return [];
      }
      throw err;
    }
  },

  add: async (payload: { questionId: string; userAnswerId?: string; notes?: string }): Promise<MistakeQuestion> => {
    return fetchApi<MistakeQuestion>('/api/mistakes', {
      method: 'POST',
      body: payload,
    });
  },

  remove: async (id: string): Promise<void> => {
    if (USE_MOCKS) return;
    return fetchApi<void>(`/api/mistakes/${id}`, {
      method: 'DELETE',
    });
  },

  practice: async (params: { subject?: string; topic?: string; count?: number } = {}): Promise<any> => {
    return fetchApi<any>('/api/mistakes/practice', {
      params,
    });
  },
};
