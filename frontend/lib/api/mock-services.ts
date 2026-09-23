import {
  MockTest,
  Attempt,
  Result,
  Question,
  PDFDocument,
  PDFProcessingJob,
  Topic,
  Subject
} from '@/types';

// Mock Data Generators

export const mockSubjects: Subject[] = [
  { id: 'sub-1', name: 'Mathematics' },
  { id: 'sub-2', name: 'Reasoning' },
  { id: 'sub-3', name: 'Physics' },
  { id: 'sub-4', name: 'Chemistry' },
  { id: 'sub-5', name: 'Biology' },
];

export const mockTopics: Topic[] = [
  { id: 'top-1', subjectId: 'sub-1', name: 'Algebra' },
  { id: 'top-2', subjectId: 'sub-1', name: 'Geometry' },
  { id: 'top-3', subjectId: 'sub-2', name: 'Syllogism' },
];

export const mockQuestions: Question[] = Array.from({ length: 20 }).map((_, i) => ({
  id: `q-${i + 1}`,
  subjectId: mockSubjects[i % 5].id,
  topicId: mockTopics[0].id,
  text: `This is a sample question ${i + 1} for RRB ALP preparation. What is the correct answer?`,
  options: [
    { id: 'opt-1', text: `Option A for Q${i + 1}` },
    { id: 'opt-2', text: `Option B for Q${i + 1}` },
    { id: 'opt-3', text: `Option C for Q${i + 1}` },
    { id: 'opt-4', text: `Option D for Q${i + 1}` },
  ],
  correctOptionId: 'opt-1',
  difficulty: i % 2 === 0 ? 'Easy' : 'Medium',
  source: 'RRB ALP - 2018',
  explanation: `Explanation for question ${i + 1}. Option A is correct because...`
}));

export const getMockTest = (id: string): MockTest => ({
  id,
  title: 'Full Mock Test 1',
  durationMinutes: 60,
  totalQuestions: 20,
  subjects: mockSubjects.map(s => s.id),
  createdAt: new Date().toISOString(),
});

export const getMockAttempt = (id: string, testId: string): Attempt => ({
  id,
  testId,
  userId: 'user-1',
  startTime: new Date().toISOString(),
  status: 'IN_PROGRESS',
  answers: {}
});

export const getMockResult = (attemptId: string): Result => ({
  id: `res-${attemptId}`,
  attemptId,
  testId: 'test-1',
  score: 15,
  totalQuestions: 20,
  correctAnswers: 15,
  wrongAnswers: 2,
  unanswered: 3,
  accuracy: 88,
  timeSpentSeconds: 3000,
  subjectPerformance: [
    { subjectId: 'sub-1', subjectName: 'Mathematics', total: 4, correct: 3, wrong: 1, unanswered: 0, accuracy: 75 }
  ],
  topicPerformance: [],
  weakTopics: ['top-1']
});
