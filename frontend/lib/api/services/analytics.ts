import { fetchApi, USE_MOCKS } from '../client';
import { AnalyticsDashboard } from '@/types';

export const analyticsApi = {
  getDashboardData: async (): Promise<AnalyticsDashboard> => {
    if (USE_MOCKS) {
      await new Promise(res => setTimeout(res, 400));
      return {
        totalTestsTaken: 4,
        averageScore: 68,
        averageAccuracy: 82,
        latestScore: 75,
        totalQuestionsAttempted: 120,
        scoreHistory: [
          { date: 'Test 1', score: 65, testId: '1' },
          { date: 'Test 2', score: 68, testId: '2' },
          { date: 'Test 3', score: 72, testId: '3' },
          { date: 'Test 4', score: 75, testId: '4' },
        ],
        subjectStrengths: [
          { subjectName: 'Mathematics', accuracy: 85 },
          { subjectName: 'Reasoning', accuracy: 80 },
          { subjectName: 'Physics', accuracy: 55 },
          { subjectName: 'Chemistry', accuracy: 65 },
          { subjectName: 'Biology', accuracy: 70 },
        ],
        recentTests: [
          { id: '1', title: 'Mock Test 1', score: 75, date: new Date().toISOString() },
        ],
        weakSubjects: ['Physics'],
        weakTopics: ['Kinematics'],
      };
    }

    try {
      // Try /api/analytics first (as in API_CONTRACT.md), then fallback to /api/analytics/dashboard
      let data: any;
      try {
        data = await fetchApi<any>('/api/analytics');
      } catch {
        data = await fetchApi<any>('/api/analytics/dashboard');
      }

      // Normalize fields
      const averageScore = Number(data.averageScore ?? data.average_score ?? 0);
      const averageAccuracy = Number(data.averageAccuracy ?? data.average_accuracy ?? 0);
      const totalTestsTaken = Number(data.totalTestsTaken ?? data.total_attempts ?? data.total_tests ?? 0);
      const latestScore = Number(data.latestScore ?? data.latest_score ?? averageScore);

      return {
        totalTestsTaken,
        averageScore,
        averageAccuracy,
        latestScore,
        totalQuestionsAttempted: data.totalQuestionsAttempted ?? data.total_questions_attempted,
        mostAttemptedSubject: data.mostAttemptedSubject ?? data.most_attempted_subject,
        bestSubject: data.bestSubject ?? data.best_subject,
        weakSubject: data.weakSubject ?? data.weak_subject,
        scoreHistory: data.scoreHistory || data.score_history || [],
        subjectStrengths: data.subjectStrengths || data.subject_strengths || [],
        recentTests: data.recentTests || data.recent_tests || [],
        weakSubjects: data.weakSubjects || data.weak_subjects || (data.weakSubject ? [data.weakSubject] : []),
        weakTopics: data.weakTopics || data.weak_topics || [],
      };
    } catch (err) {
      if (USE_MOCKS) {
        return {
          totalTestsTaken: 0,
          averageScore: 0,
          averageAccuracy: 0,
          scoreHistory: [],
          subjectStrengths: [],
        };
      }
      throw err;
    }
  },
};
