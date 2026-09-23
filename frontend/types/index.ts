// Authoritative API & Domain Types for RRB ALP Mock Test Platform

export type UUID = string;

// ==========================================
// Authentication & Users
// ==========================================
export interface User {
  id: UUID;
  name: string;
  email: string;
  avatarUrl?: string;
  createdAt?: string;
}

export interface AuthResponse {
  user: User;
  token: string;
}

export interface GoogleLoginUrlResponse {
  authorization_url: string;
}

// ==========================================
// Subjects & Topics
// ==========================================
export interface Subject {
  id: UUID;
  name: string;
  code?: string;
  short_code?: string;
  description?: string;
  display_order?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface Topic {
  id: UUID;
  subjectId: UUID;
  name: string;
  code?: string;
  description?: string;
}

// ==========================================
// Questions
// ==========================================
export type QuestionDifficulty = 'EASY' | 'MEDIUM' | 'HARD' | 'Easy' | 'Medium' | 'Hard';
export type QuestionSourceType = 'PYQ' | 'AI_GENERATED' | 'REFERENCE' | 'MIXED' | 'PYQ Only';
export type VerificationStatus = 'VERIFIED' | 'NEEDS_REVIEW' | 'REJECTED' | 'UNVERIFIED';

export interface QuestionOption {
  id: string;
  text: string;
}

export interface Question {
  id: UUID;
  subjectId: UUID;
  topicId?: UUID;
  text: string;
  options: QuestionOption[];
  correctOptionId?: string; // Omitted in student exam mode to prevent answer leakage
  explanation?: string;     // Omitted in student exam mode
  difficulty: QuestionDifficulty;
  sourceType?: QuestionSourceType;
  source?: string;
  sourceYear?: number | null;
  sourceExam?: string | null;
  verificationStatus?: VerificationStatus;
  pdfSourceId?: string | null;
}

// ==========================================
// Mock Tests
// ==========================================
export interface MockTestConfig {
  questionCount: number;
  subjects: string[]; // Subject UUIDs or Names
  topics?: string[];
  difficulty: 'EASY' | 'MEDIUM' | 'HARD' | 'MIXED' | 'Easy' | 'Medium' | 'Hard' | 'Mixed';
  source?: 'PYQ' | 'AI_GENERATED' | 'MIXED' | 'PYQ Only' | 'AI Generated' | 'Mixed';
  durationMinutes?: number;
  title?: string;
  subjectWeights?: Record<string, number>;
}

export interface MockTest {
  id: UUID;
  title: string;
  description?: string;
  durationMinutes: number;
  totalQuestions: number;
  subjects: string[];
  createdAt: string;
  isCompleted?: boolean;
}

export interface MockTestDetailResponse {
  test: MockTest;
  questions: Question[];
}

// ==========================================
// Exam Attempts & Autosave
// ==========================================
export type QuestionStatus = 
  | 'UNANSWERED' 
  | 'ANSWERED' 
  | 'MARKED' 
  | 'ANSWERED_AND_MARKED' 
  | 'NOT_VISITED';

export interface AttemptAnswer {
  questionId: UUID;
  selectedOptionId?: string;
  status: QuestionStatus;
  timeSpentSeconds?: number;
}

export type SelectedAnswerOption = 'A' | 'B' | 'C' | 'D' | null;

export interface BackendAttempt {
  id: string;
  user_id: string;
  mock_test_id: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'EXPIRED' | string;
  started_at: string | null;
  expires_at: string | null;
  submitted_at: string | null;
  auto_submitted: boolean;
  created_at: string;
  updated_at: string;
}

export interface AttemptStatus {
  id: string;
  mock_test_id: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'EXPIRED' | string;
  started_at: string | null;
  expires_at: string | null;
  seconds_remaining: number | null;
  total_questions: number;
  answered_count: number;
  marked_count: number;
  answers: AnswerSave[];
}

export interface AnswerSave {
  question_id: string;
  selected_answer: SelectedAnswerOption;
  is_marked: boolean;
}

export interface AnswerSaveRequest {
  answers: AnswerSave[];
}

export interface SubmitResponse {
  attempt_id: string;
  result_id: string;
  message: string;
}

export interface Attempt {
  id: UUID;
  testId: UUID;
  userId?: UUID;
  startTime: string; // ISO String
  endTime?: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'SUBMITTED' | 'EXPIRED' | 'COMPLETED' | 'ABANDONED';
  answers: Record<UUID, AttemptAnswer | string>; // Map or object
  seconds_remaining?: number | null; // Authoritative backend seconds remaining
  expires_at?: string | null;
  started_at?: string | null;
}

export type SaveAnswersPayload = AnswerSaveRequest;

// ==========================================
// Results & Analytics
// ==========================================
export interface SubjectPerformance {
  subjectId: UUID;
  subjectName: string;
  score?: number;
  total: number;
  correct: number;
  wrong: number;
  incorrect?: number;
  unanswered?: number;
  accuracy: number;
}

export interface TopicPerformance {
  topicId: UUID;
  topicName: string;
  subjectId: UUID;
  total: number;
  correct: number;
  wrong: number;
  accuracy: number;
}

export interface Result {
  id: UUID;
  attemptId: UUID;
  testId?: UUID;
  score: number;
  maxScore?: number;
  totalQuestions: number;
  attempted?: number;
  correctAnswers: number;
  wrongAnswers: number;
  unanswered: number;
  accuracy: number;
  timeSpentSeconds: number;
  subjectPerformance: SubjectPerformance[];
  topicPerformance?: TopicPerformance[];
  weakTopics?: string[];
}

export interface ScoreHistoryItem {
  date: string;
  score: number;
  testId: string;
}

export interface SubjectStrength {
  subjectName: string;
  accuracy: number;
}

export interface AnalyticsDashboard {
  totalTestsTaken: number;
  averageScore: number;
  averageAccuracy: number;
  latestScore?: number;
  totalQuestionsAttempted?: number;
  mostAttemptedSubject?: string;
  bestSubject?: string;
  weakSubject?: string;
  scoreHistory?: ScoreHistoryItem[];
  subjectStrengths?: SubjectStrength[];
  recentTests?: Array<{
    id: string;
    title: string;
    score: number;
    date: string;
  }>;
  weakSubjects?: string[];
  weakTopics?: string[];
}

// ==========================================
// Mistake Book
// ==========================================
export interface MistakeQuestion {
  id: UUID;
  questionId: UUID;
  attemptId?: UUID;
  userAnswerId?: string | null;
  addedAt?: string;
  savedAt?: string;
  notes?: string;
  question: Question;
}

// ==========================================
// PDF Processing
// ==========================================
export type PDFProcessingStatus = 
  | 'QUEUED' 
  | 'UPLOADING' 
  | 'PROCESSING' 
  | 'EXTRACTING' 
  | 'OCR' 
  | 'PARSING' 
  | 'VALIDATING' 
  | 'COMPLETED' 
  | 'FAILED';

export interface PDFDocument {
  id: UUID;
  filename: string;
  sizeBytes?: number;
  uploadedAt: string;
  status?: PDFProcessingStatus;
  questionCount?: number;
  processingJobId?: string;
}

export interface PDFProcessingJob {
  id: UUID;
  jobId?: UUID;
  documentId?: UUID;
  status: PDFProcessingStatus;
  progress?: number; // 0-100
  progress_pct?: number;
  current_stage?: string;
  error?: string | null;
  error_message?: string | null;
  message?: string;
}

export interface PDFUploadResponse {
  jobId?: string;
  job_id?: string;
  documentId?: string;
  document_id?: string;
  status: PDFProcessingStatus;
  progress?: number;
  progress_pct?: number;
}
