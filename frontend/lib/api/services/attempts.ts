import { fetchApi, USE_MOCKS, ApiError } from '../client';
import { 
  BackendAttempt, 
  AttemptStatus, 
  AnswerSave, 
  AnswerSaveRequest, 
  SubmitResponse 
} from '@/types';

export const attemptApi = {
  /**
   * 1. Create Attempt (NOT_STARTED)
   * POST /api/attempts
   * Request: { "mock_test_id": "UUID" }
   */
  create: async (mockTestId: string): Promise<BackendAttempt> => {
    if (USE_MOCKS) {
      await new Promise(res => setTimeout(res, 300));
      return {
        id: 'att-' + Date.now(),
        user_id: 'mock-user-1',
        mock_test_id: mockTestId,
        status: 'NOT_STARTED',
        started_at: null,
        expires_at: null,
        submitted_at: null,
        auto_submitted: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }

    try {
      return await fetchApi<BackendAttempt>('/api/attempts', {
        method: 'POST',
        body: {
          mock_test_id: mockTestId,
        },
      });
    } catch (err: any) {
      // If 409 Conflict occurs (attempt already exists or in progress), return existing attempt id info if provided
      if (err instanceof ApiError && err.status === 409 && err.data?.attempt_id) {
        return {
          id: err.data.attempt_id,
          user_id: '',
          mock_test_id: mockTestId,
          status: 'IN_PROGRESS',
          started_at: null,
          expires_at: null,
          submitted_at: null,
          auto_submitted: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
      }
      throw err;
    }
  },

  /**
   * 2. Start Attempt (NOT_STARTED -> IN_PROGRESS)
   * POST /api/attempts/{attempt_id}/start
   * Sets started_at and expires_at on the server.
   */
  start: async (attemptId: string): Promise<BackendAttempt> => {
    if (USE_MOCKS) {
      await new Promise(res => setTimeout(res, 200));
      const now = new Date();
      const expires = new Date(now.getTime() + 60 * 60 * 1000);
      return {
        id: attemptId,
        user_id: 'mock-user-1',
        mock_test_id: 'mock-test-1',
        status: 'IN_PROGRESS',
        started_at: now.toISOString(),
        expires_at: expires.toISOString(),
        submitted_at: null,
        auto_submitted: false,
        created_at: now.toISOString(),
        updated_at: now.toISOString(),
      };
    }

    return await fetchApi<BackendAttempt>(`/api/attempts/${attemptId}/start`, {
      method: 'POST',
    });
  },

  /**
   * 3. Get Attempt Live Status
   * GET /api/attempts/{attempt_id}/status
   * Returns authoritative seconds_remaining, status, total_questions, etc.
   */
  getStatus: async (attemptId: string): Promise<AttemptStatus> => {
    if (USE_MOCKS) {
      return {
        id: attemptId,
        mock_test_id: 'mock-test-1',
        status: 'IN_PROGRESS',
        started_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
        seconds_remaining: 3600,
        total_questions: 20,
        answered_count: 0,
        marked_count: 0,
        answers: [],
      };
    }

    return await fetchApi<AttemptStatus>(`/api/attempts/${attemptId}/status`);
  },

  /**
   * 4. Save Answers
   * POST /api/attempts/{attempt_id}/answers
   * Request MUST be: { "answers": [ { "question_id": "UUID", "selected_answer": "A"|"B"|"C"|"D"|null, "is_marked": boolean } ] }
   */
  saveAnswers: async (attemptId: string, answers: AnswerSave[]): Promise<void> => {
    if (USE_MOCKS) return;
    if (!answers || answers.length === 0) return;

    const payload: AnswerSaveRequest = { answers };

    return await fetchApi<void>(`/api/attempts/${attemptId}/answers`, {
      method: 'POST',
      body: payload,
    });
  },

  /**
   * 5. Submit Attempt
   * POST /api/attempts/{attempt_id}/submit
   * Response: { "attempt_id": "UUID", "result_id": "UUID", "message": "..." }
   */
  submit: async (attemptId: string): Promise<SubmitResponse> => {
    if (USE_MOCKS) {
      await new Promise(res => setTimeout(res, 500));
      return {
        attempt_id: attemptId,
        result_id: `res-${attemptId}`,
        message: 'Attempt submitted successfully.',
      };
    }

    const res = await fetchApi<SubmitResponse>(`/api/attempts/${attemptId}/submit`, {
      method: 'POST',
    });

    if (!res || !res.result_id) {
      throw new ApiError('Attempt submission succeeded but no result_id was returned from the server.', 500, res);
    }

    return res;
  },
};
