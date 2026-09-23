import { create } from 'zustand';
import { AttemptAnswer, QuestionStatus, SelectedAnswerOption, AnswerSave, AttemptStatus } from '@/types';
import { attemptApi } from '@/lib/api/services';
import { toSelectedAnswer, fromSelectedAnswer } from '@/lib/utils/answers';
import { ApiError } from '@/lib/api/client';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface PendingAnswerItem {
  selected_answer: SelectedAnswerOption;
  is_marked: boolean;
}

interface ExamState {
  attemptId: string | null;
  testId: string | null;
  answers: Record<string, AttemptAnswer>;
  currentQuestionIndex: number;
  timeRemainingSeconds: number | null;
  saveStatus: SaveStatus;
  isExpired: boolean;
  isSubmitted: boolean;

  initExam: (
    attemptId: string, 
    testId: string, 
    serverSecondsRemaining: number, 
    initialAnswers?: AnswerSave[] | Record<string, any>
  ) => void;
  setAnswer: (questionId: string, optionId: string | undefined, status: QuestionStatus, options?: { id: string }[]) => void;
  clearAnswer: (questionId: string) => void;
  setCurrentQuestion: (index: number) => void;
  tickTimer: () => void;
  setTimeRemaining: (seconds: number | null) => void;
  syncServerStatus: (status: AttemptStatus) => void;
  flushPendingSaves: () => Promise<void>;
}

// Queue management to avoid race conditions and preserve updates
let saveTimeout: NodeJS.Timeout | null = null;
let pendingQueue: Record<string, PendingAnswerItem> = {};
let inFlightQueue: Record<string, PendingAnswerItem> | null = null;
let isSaving = false;

async function processQueue(attemptId: string, set: any, get: any): Promise<void> {
  if (isSaving) return;
  if (Object.keys(pendingQueue).length === 0) {
    if (get().saveStatus === 'saving') {
      set({ saveStatus: 'idle' });
    }
    return;
  }

  isSaving = true;
  set({ saveStatus: 'saving' });

  // Snapshot current pending queue and reset it for new incoming edits
  inFlightQueue = { ...pendingQueue };
  pendingQueue = {};

  const payload: AnswerSave[] = Object.entries(inFlightQueue).map(([question_id, val]) => ({
    question_id,
    selected_answer: val.selected_answer,
    is_marked: val.is_marked,
  }));

  try {
    await attemptApi.saveAnswers(attemptId, payload);
    inFlightQueue = null;
    isSaving = false;
    set({ saveStatus: 'saved' });

    setTimeout(() => {
      if (get().saveStatus === 'saved' && Object.keys(pendingQueue).length === 0) {
        set({ saveStatus: 'idle' });
      }
    }, 2000);

    // If new changes arrived while the request was in flight, process them immediately
    if (Object.keys(pendingQueue).length > 0) {
      await processQueue(attemptId, set, get);
    }
  } catch (err: any) {
    console.error('Failed to save answers to server', err);
    isSaving = false;

    // Handle 409 Conflict: attempt might be expired or already submitted
    if (err instanceof ApiError && err.status === 409) {
      try {
        const liveStatus = await attemptApi.getStatus(attemptId);
        get().syncServerStatus(liveStatus);
      } catch (statusErr) {
        console.error('Failed to fetch status after 409', statusErr);
      }
      inFlightQueue = null;
      set({ saveStatus: 'error' });
      return;
    }

    // Merge failed in-flight items back into pendingQueue without overwriting newer edits
    if (inFlightQueue) {
      for (const [qId, val] of Object.entries(inFlightQueue)) {
        if (!pendingQueue[qId]) {
          pendingQueue[qId] = val;
        }
      }
      inFlightQueue = null;
    }
    set({ saveStatus: 'error' });
  }
}

export const useExamStore = create<ExamState>((set, get) => ({
  attemptId: null,
  testId: null,
  answers: {},
  currentQuestionIndex: 0,
  timeRemainingSeconds: null,
  saveStatus: 'idle',
  isExpired: false,
  isSubmitted: false,

  initExam: (attemptId, testId, serverSecondsRemaining, initialAnswers = []) => {
    // Clear any previous queues
    if (saveTimeout) clearTimeout(saveTimeout);
    pendingQueue = {};
    inFlightQueue = null;
    isSaving = false;

    const normalizedAnswers: Record<string, AttemptAnswer> = {};

    if (Array.isArray(initialAnswers)) {
      initialAnswers.forEach((ans: any) => {
        const qId = ans.question_id || ans.questionId;
        if (!qId) return;

        const selected = ans.selected_answer || ans.selectedOptionId || undefined;
        const isMarked = Boolean(ans.is_marked || ans.status === 'MARKED' || ans.status === 'ANSWERED_AND_MARKED');
        let status: QuestionStatus = 'UNANSWERED';

        if (selected && isMarked) {
          status = 'ANSWERED_AND_MARKED';
        } else if (selected) {
          status = 'ANSWERED';
        } else if (isMarked) {
          status = 'MARKED';
        }

        normalizedAnswers[qId] = {
          questionId: qId,
          selectedOptionId: selected,
          status,
        };
      });
    } else if (initialAnswers && typeof initialAnswers === 'object') {
      Object.entries(initialAnswers).forEach(([qId, val]) => {
        if (typeof val === 'string') {
          normalizedAnswers[qId] = {
            questionId: qId,
            selectedOptionId: val,
            status: 'ANSWERED',
          };
        } else if (val && typeof val === 'object') {
          const actualQId = (val as any).question_id || (val as any).questionId || qId;
          const selected = val.selectedOptionId || (val as any).selected_answer || undefined;
          const isMarked = Boolean(val.is_marked || val.status === 'MARKED' || val.status === 'ANSWERED_AND_MARKED');
          let status: QuestionStatus = 'UNANSWERED';

          if (selected && isMarked) {
            status = 'ANSWERED_AND_MARKED';
          } else if (selected) {
            status = 'ANSWERED';
          } else if (isMarked) {
            status = 'MARKED';
          }

          normalizedAnswers[actualQId] = {
            questionId: actualQId,
            selectedOptionId: selected,
            status,
          };
        }
      });
    }

    set({
      attemptId,
      testId,
      answers: normalizedAnswers,
      timeRemainingSeconds: serverSecondsRemaining,
      currentQuestionIndex: 0,
      saveStatus: 'idle',
      isExpired: false,
      isSubmitted: false,
    });
  },

  setAnswer: (questionId, optionId, status, options) => {
    const { attemptId } = get();
    if (!attemptId) return;

    // Update UI state immediately
    const newAnswer: AttemptAnswer = {
      questionId,
      selectedOptionId: optionId,
      status,
    };

    set(state => ({
      answers: { ...state.answers, [questionId]: newAnswer },
      saveStatus: 'saving',
    }));

    // Queue canonical AnswerSave payload
    const canonicalAnswer = toSelectedAnswer(optionId, options as any);
    const isMarked = status === 'MARKED' || status === 'ANSWERED_AND_MARKED';

    pendingQueue[questionId] = {
      selected_answer: canonicalAnswer,
      is_marked: isMarked,
    };

    // Debounced network save
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      const currentAttempt = get().attemptId;
      if (currentAttempt) {
        processQueue(currentAttempt, set, get);
      }
    }, 500);
  },

  clearAnswer: (questionId) => {
    const { attemptId, answers } = get();
    if (!attemptId) return;

    const prevAnswer = answers[questionId];
    // Preserve marked-for-review state if previously marked
    const wasMarked = prevAnswer?.status === 'MARKED' || prevAnswer?.status === 'ANSWERED_AND_MARKED';
    const newStatus: QuestionStatus = wasMarked ? 'MARKED' : 'UNANSWERED';

    const newAnswer: AttemptAnswer = {
      questionId,
      selectedOptionId: undefined,
      status: newStatus,
    };

    set(state => ({
      answers: { ...state.answers, [questionId]: newAnswer },
      saveStatus: 'saving',
    }));

    pendingQueue[questionId] = {
      selected_answer: null,
      is_marked: wasMarked,
    };

    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      const currentAttempt = get().attemptId;
      if (currentAttempt) {
        processQueue(currentAttempt, set, get);
      }
    }, 500);
  },

  setCurrentQuestion: (index) => {
    set({ currentQuestionIndex: index });
  },

  tickTimer: () => {
    set(state => {
      if (state.timeRemainingSeconds === null) return state;
      if (state.timeRemainingSeconds <= 1) {
        return { timeRemainingSeconds: 0, isExpired: true };
      }
      return { timeRemainingSeconds: state.timeRemainingSeconds - 1 };
    });
  },

  setTimeRemaining: (seconds) => {
    set(state => ({
      timeRemainingSeconds: seconds,
      isExpired: seconds !== null && seconds <= 0,
    }));
  },

  syncServerStatus: (status) => {
    const isExpired = status.status === 'EXPIRED' || (status.seconds_remaining !== null && status.seconds_remaining <= 0);
    const isSubmitted = status.status === 'SUBMITTED';

    set(state => {
      const updatedAnswers = { ...state.answers };

      if (Array.isArray(status.answers)) {
        status.answers.forEach((ans) => {
          const qId = ans.question_id;
          if (!qId) return;

          // Only sync if question is not in pendingQueue or inFlightQueue
          if (!pendingQueue[qId] && (!inFlightQueue || !inFlightQueue[qId])) {
            const selected = ans.selected_answer || undefined;
            const isMarked = Boolean(ans.is_marked);
            let qStatus: QuestionStatus = 'UNANSWERED';

            if (selected && isMarked) {
              qStatus = 'ANSWERED_AND_MARKED';
            } else if (selected) {
              qStatus = 'ANSWERED';
            } else if (isMarked) {
              qStatus = 'MARKED';
            }

            // Preserve local option mapping if already present
            const existingOptId = state.answers[qId]?.selectedOptionId;
            const chosenOptId = existingOptId && toSelectedAnswer(existingOptId) === ans.selected_answer
              ? existingOptId
              : selected;

            updatedAnswers[qId] = {
              questionId: qId,
              selectedOptionId: chosenOptId,
              status: qStatus,
            };
          }
        });
      }

      return {
        answers: updatedAnswers,
        timeRemainingSeconds: status.seconds_remaining,
        isExpired,
        isSubmitted,
      };
    });
  },

  flushPendingSaves: async () => {
    const { attemptId } = get();
    if (!attemptId) return;

    if (saveTimeout) {
      clearTimeout(saveTimeout);
      saveTimeout = null;
    }

    // Process all pending items until queues are empty
    let attempts = 0;
    while ((Object.keys(pendingQueue).length > 0 || isSaving) && attempts < 50) {
      attempts++;
      await processQueue(attemptId, set, get);
      if (isSaving) {
        // Wait briefly for in-flight save to complete
        await new Promise(res => setTimeout(res, 100));
      }
      if (get().saveStatus === 'error') {
        if (get().isExpired || get().isSubmitted) {
          break;
        }
        throw new Error('Failed to autosave all answers prior to submission. Please verify your connection.');
      }
    }
  },
}));
