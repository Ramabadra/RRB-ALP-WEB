import { fetchApi, USE_MOCKS } from '../client';
import { Question, QuestionOption } from '@/types';
import { mockQuestions } from '../mock-services';

export interface QuestionFilters {
  subjectId?: string;
  topicId?: string;
  difficulty?: string;
  sourceType?: string;
  page?: number;
  pageSize?: number;
}

export function normalizeQuestion(raw: any): Question {
  if (!raw) {
    return {
      id: '',
      subjectId: '',
      text: '',
      options: [],
      difficulty: 'MEDIUM',
    };
  }

  const id = raw.id ?? raw.question_id ?? '';
  const text = raw.text ?? raw.question_text ?? raw.question ?? '';
  const subjectId = raw.subjectId ?? raw.subject_id ?? '';
  const topicId = raw.topicId ?? raw.topic_id ?? undefined;
  const difficulty = raw.difficulty ?? 'MEDIUM';
  const sourceType = raw.sourceType ?? raw.source_type ?? 'MIXED';

  let options: QuestionOption[] = [];

  if (Array.isArray(raw.options)) {
    options = raw.options.map((opt: any, idx: number) => {
      if (typeof opt === 'string') {
        const optionId = ['A', 'B', 'C', 'D'][idx] || String(idx + 1);
        return { id: optionId, text: opt };
      }
      const optionId = opt.id ?? opt.key ?? ['A', 'B', 'C', 'D'][idx] ?? String(idx + 1);
      const optionText = opt.text ?? opt.option_text ?? opt.value ?? '';
      return { id: String(optionId), text: String(optionText) };
    });
  } else if (raw.options && typeof raw.options === 'object') {
    options = Object.entries(raw.options).map(([key, val]) => ({
      id: key,
      text: String(val),
    }));
  } else if (raw.option_a || raw.option_b || raw.option_c || raw.option_d) {
    options = [
      { id: 'A', text: String(raw.option_a || '') },
      { id: 'B', text: String(raw.option_b || '') },
      { id: 'C', text: String(raw.option_c || '') },
      { id: 'D', text: String(raw.option_d || '') },
    ].filter(o => o.text !== '');
  }

  return {
    id,
    subjectId,
    topicId,
    text,
    options,
    difficulty,
    sourceType,
    source: raw.source,
    sourceYear: raw.sourceYear ?? raw.source_year ?? null,
    sourceExam: raw.sourceExam ?? raw.source_exam ?? null,
    verificationStatus: raw.verificationStatus ?? raw.verification_status,
    pdfSourceId: raw.pdfSourceId ?? raw.pdf_source_id ?? null,
  };
}

export const questionsApi = {
  getQuestions: async (filters: QuestionFilters = {}): Promise<Question[]> => {
    if (USE_MOCKS) {
      let list = [...mockQuestions];
      if (filters.subjectId) list = list.filter(q => q.subjectId === filters.subjectId);
      if (filters.difficulty) list = list.filter(q => q.difficulty.toLowerCase() === filters.difficulty?.toLowerCase());
      return list;
    }

    try {
      const data = await fetchApi<any>('/api/questions', {
        params: {
          subjectId: filters.subjectId,
          subject_id: filters.subjectId,
          topicId: filters.topicId,
          topic_id: filters.topicId,
          difficulty: filters.difficulty?.toUpperCase(),
          source_type: filters.sourceType,
          page: filters.page,
          page_size: filters.pageSize,
        },
      });

      // Normalize if backend returns paginated object { items: Question[] } or array Question[]
      let items: any[] = [];
      if (Array.isArray(data)) {
        items = data;
      } else if (data && Array.isArray(data.items)) {
        items = data.items;
      }
      return items.map(normalizeQuestion);
    } catch (err) {
      if (USE_MOCKS) return mockQuestions;
      throw err;
    }
  },

  getById: async (id: string): Promise<Question> => {
    const raw = await fetchApi<any>(`/api/questions/${id}`);
    return normalizeQuestion(raw);
  },

  // AI Question Generation (via FastAPI backend)
  generateAIQuestions: async (payload: { subjectId: string; topicId?: string; count?: number; difficulty?: string }): Promise<Question[]> => {
    return fetchApi<Question[]>('/api/questions/generate', {
      method: 'POST',
      body: payload,
    });
  },

  // AI Question Validation (via FastAPI backend)
  validateQuestion: async (questionId: string): Promise<{ isValid: boolean; feedback?: string }> => {
    return fetchApi<{ isValid: boolean; feedback?: string }>(`/api/questions/${questionId}/validate`, {
      method: 'POST',
    });
  },
};
