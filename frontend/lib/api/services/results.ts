import { fetchApi, USE_MOCKS } from '../client';
import { Result } from '@/types';
import * as mockData from '../mock-services';

export const resultsApi = {
  getById: async (attemptId: string): Promise<Result> => {
    if (USE_MOCKS) {
      await new Promise(res => setTimeout(res, 400));
      return mockData.getMockResult(attemptId);
    }

    const data = await fetchApi<any>(`/api/results/${attemptId}`);

    // Robust adapter: normalize backend fields to frontend Result model
    const totalQuestions = data.totalQuestions ?? data.total_questions ?? 0;
    const correctAnswers = data.correct ?? data.correctAnswers ?? data.correct_answers ?? 0;
    const wrongAnswers = data.incorrect ?? data.wrong ?? data.wrongAnswers ?? data.wrong_answers ?? 0;
    const attempted = data.attempted ?? (correctAnswers + wrongAnswers);
    const unanswered = data.unanswered ?? Math.max(0, totalQuestions - attempted);

    const subjectPerformance = (data.subjectPerformance || data.subject_performance || []).map((sub: any) => ({
      subjectId: sub.subjectId || sub.subject_id || '',
      subjectName: sub.subjectName || sub.subject_name || sub.name || 'General',
      score: sub.score ?? 0,
      total: sub.total ?? sub.total_questions ?? 0,
      correct: sub.correct ?? 0,
      wrong: sub.incorrect ?? sub.wrong ?? 0,
      incorrect: sub.incorrect ?? sub.wrong ?? 0,
      unanswered: sub.unanswered ?? 0,
      accuracy: sub.accuracy ?? (sub.total > 0 ? Math.round((sub.correct / sub.total) * 100) : 0),
    }));

    return {
      id: data.id || `res-${attemptId}`,
      attemptId: data.attemptId || data.attempt_id || attemptId,
      testId: data.testId || data.test_id,
      score: Number(data.score ?? 0),
      maxScore: Number(data.maxScore ?? data.max_score ?? totalQuestions),
      totalQuestions,
      attempted,
      correctAnswers,
      wrongAnswers,
      unanswered,
      accuracy: Number(data.accuracy ?? (attempted > 0 ? Math.round((correctAnswers / attempted) * 100) : 0)),
      timeSpentSeconds: Number(data.timeSpentSeconds ?? data.time_spent_seconds ?? 0),
      subjectPerformance,
      topicPerformance: data.topicPerformance || data.topic_performance || [],
      weakTopics: data.weakTopics || data.weak_topics || [],
    };
  },

  list: async (page = 1): Promise<Result[]> => {
    try {
      const data = await fetchApi<any>('/api/results', {
        params: { page },
      });
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.items)) return data.items;
      return [];
    } catch {
      return [];
    }
  },
};
