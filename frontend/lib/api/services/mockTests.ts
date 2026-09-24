import { fetchApi, USE_MOCKS } from '../client';
import { MockTestConfig, MockTest, MockTestDetailResponse, Question } from '@/types';
import * as mockData from '../mock-services';
import { questionsApi, normalizeQuestion } from './questions';

export const mockTestApi = {
  generate: async (config: MockTestConfig): Promise<MockTest> => {
    if (USE_MOCKS) {
      await new Promise(res => setTimeout(res, 600));
      return mockData.getMockTest('test-' + Date.now());
    }

    // Build subject weights if not provided
    const subjectWeights: Record<string, number> = config.subjectWeights || {};
    if (Object.keys(subjectWeights).length === 0 && config.subjects.length > 0) {
      const weightPerSubject = Math.floor(100 / config.subjects.length);
      config.subjects.forEach(sub => {
        subjectWeights[sub] = weightPerSubject;
      });
    }

    // Adapt payload to fulfill API_CONTRACT.md and FastAPI backend expectations
    const payload = {
      // API_CONTRACT.md fields
      subjectWeights,
      totalQuestions: config.questionCount,
      durationMinutes: config.durationMinutes || (config.questionCount <= 30 ? 30 : 60),
      difficulty: config.difficulty.toUpperCase(),

      // FastAPI backend compatibility aliases
      question_count: config.questionCount,
      subjects: config.subjects,
      topics: config.topics || [],
      source_type: (config.source || 'MIXED').toUpperCase().replace(' ONLY', '').replace(' GENERATED', '_GENERATED'),
      duration_minutes: config.durationMinutes || (config.questionCount <= 30 ? 30 : 60),
      negative_marking: 0.3333,
      marks_per_correct: 1.0,
      title: config.title || `RRB ALP ${config.questionCount}-Question Mock Test`,
    };

    return fetchApi<MockTest>('/api/mock-tests', {
      method: 'POST',
      body: payload,
    });
  },

  list: async (): Promise<MockTest[]> => {
    if (USE_MOCKS) {
      return [
        mockData.getMockTest('1'),
        { ...mockData.getMockTest('2'), title: 'Mathematics Sectional', durationMinutes: 30, totalQuestions: 25 },
      ];
    }
    try {
      const data = await fetchApi<any>('/api/mock-tests');
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
    } catch (err) {
      if (USE_MOCKS) return [mockData.getMockTest('1')];
      throw err;
    }
  },

  getById: async (id: string): Promise<MockTestDetailResponse> => {
    if (USE_MOCKS) {
      await new Promise(res => setTimeout(res, 300));
      return {
        test: mockData.getMockTest(id),
        questions: mockData.mockQuestions,
      };
    }

    const res = await fetchApi<any>(`/api/mock-tests/${id}`);
    
    let testMeta: MockTest;
    let rawQuestions: any[] = [];

    // Normalize response structure
    if (res.test) {
      testMeta = res.test;
      rawQuestions = res.questions || res.test.questions || res.test.question_ids || [];
    } else {
      const { questions, question_ids, ...rest } = res;
      testMeta = rest as MockTest;
      rawQuestions = questions || question_ids || [];
    }

    // If questions are IDs only (strings or objects without question text/options),
    // resolve them via safe GET /api/questions/{id}
    if (
      rawQuestions.length > 0 &&
      (typeof rawQuestions[0] === 'string' || (!rawQuestions[0].text && !rawQuestions[0].question_text))
    ) {
      const questionIds: string[] = rawQuestions.map((q: any) =>
        typeof q === 'string' ? q : q.id
      );

      const resolvedQuestions: Question[] = await Promise.all(
        questionIds.map(async (qid) => {
          try {
            return await questionsApi.getById(qid);
          } catch (err) {
            console.error(`Error loading question ${qid}:`, err);
            return normalizeQuestion({ id: qid, text: `Question ${qid}`, options: [] });
          }
        })
      );

      return {
        test: testMeta,
        questions: resolvedQuestions,
      };
    }

    // Questions already contain objects, normalize with safe fields
    const normalizedQuestions: Question[] = rawQuestions.map(q => normalizeQuestion(q));

    return {
      test: testMeta,
      questions: normalizedQuestions,
    };
  },
};
