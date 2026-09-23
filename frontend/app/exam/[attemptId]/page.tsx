"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { mockTestApi, attemptApi } from "@/lib/api/services";
import { useExamStore } from "@/hooks/use-exam-store";
import { Question, MockTest } from "@/types";
import { Button } from "@/components/ui/button";
import { Menu, Maximize, Minimize, Bookmark, Clock, Loader2, Check, AlertCircle } from "lucide-react";
import { toSelectedAnswer, fromSelectedAnswer } from "@/lib/utils/answers";

export default function ExamInterface() {
  const params = useParams();
  const searchParams = useSearchParams();
  const attemptId = params.attemptId as string;
  const router = useRouter();

  const [test, setTest] = useState<MockTest | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showPalette, setShowPalette] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const autoSubmittedRef = useRef(false);

  const { 
    initExam, 
    answers, 
    currentQuestionIndex, 
    setCurrentQuestion, 
    setAnswer, 
    clearAnswer,
    timeRemainingSeconds,
    tickTimer,
    setTimeRemaining,
    syncServerStatus,
    saveStatus,
    flushPendingSaves
  } = useExamStore();

  // Full exam submission with pre-flush
  const handleAutoSubmit = useCallback(async () => {
    if (submitting || autoSubmittedRef.current) return;
    autoSubmittedRef.current = true;
    setSubmitting(true);
    setError(null);

    try {
      // 1. Flush all pending debounced saves
      await flushPendingSaves();

      // 2. Submit to backend
      const res = await attemptApi.submit(attemptId);

      // 3. Strictly require result_id
      if (!res || !res.result_id) {
        throw new Error("Exam submission succeeded but result ID was not returned by the server.");
      }

      // 4. Navigate directly to results with authoritative result_id
      router.push(`/results/${res.result_id}`);
    } catch (e: any) {
      console.error("Exam submission failed", e);
      setSubmitting(false);
      autoSubmittedRef.current = false;
      setError(e?.message || "Failed to submit exam. Please verify your connection and retry.");
    }
  }, [attemptId, flushPendingSaves, router, submitting]);

  // Initial Attempt & Test Loading Lifecycle
  useEffect(() => {
    let isMounted = true;

    async function loadExamSession() {
      try {
        setLoading(true);
        setError(null);

        // Step 1: GET /api/attempts/{attempt_id}/status
        let status = await attemptApi.getStatus(attemptId);

        // Step 2: Lifecycle check - if NOT_STARTED, transition to IN_PROGRESS via start endpoint
        if (status.status === 'NOT_STARTED') {
          await attemptApi.start(attemptId);
          status = await attemptApi.getStatus(attemptId);
        }

        if (!isMounted) return;

        // Step 3: Terminal state checks
        if (status.status === 'SUBMITTED') {
          const resultId = (status as any).result_id;
          if (resultId) {
            router.push(`/results/${resultId}`);
          } else {
            setError("This exam attempt has already been submitted.");
            setLoading(false);
          }
          return;
        }

        if (status.status === 'EXPIRED' || (status.seconds_remaining !== null && status.seconds_remaining <= 0)) {
          syncServerStatus(status);
          setError("This exam attempt has expired.");
          setLoading(false);
          return;
        }

        // Step 4: Resolve test ID to load questions directly from backend status
        const resolvedTestId = status.mock_test_id || searchParams.get('testId');

        if (!resolvedTestId) {
          throw new Error("Unable to determine mock test details for this attempt.");
        }

        const testData = await mockTestApi.getById(resolvedTestId);
        if (!isMounted) return;

        setTest(testData.test);

        // Step 5: Consume safe questions directly from backend response
        const examQuestions: Question[] = testData.questions || [];
        setQuestions(examQuestions);

        // Step 6: Server-authoritative timer setup
        const initialSeconds = status.seconds_remaining ?? ((testData.test.durationMinutes || 60) * 60);

        // Step 7: Restore persisted answers from backend status.answers
        const restoredAnswers = (status.answers || []).map(ans => {
          const matchedQ = examQuestions.find(q => q.id === ans.question_id);
          const matchedOptId = fromSelectedAnswer(ans.selected_answer, matchedQ?.options) || ans.selected_answer || undefined;
          return {
            ...ans,
            selectedOptionId: matchedOptId,
          };
        });

        // Initialize Zustand store with authoritative timer and restored answers
        initExam(attemptId, testData.test.id, initialSeconds, restoredAnswers);
        syncServerStatus(status);
        setLoading(false);
      } catch (err: any) {
        if (isMounted) {
          console.error("Failed to load exam attempt", err);
          setError(err?.message || "Failed to initialize exam session.");
          setLoading(false);
        }
      }
    }

    loadExamSession();

    return () => {
      isMounted = false;
    };
  }, [attemptId, searchParams, router, initExam, syncServerStatus]);

  // Periodic Timer & Status Resynchronization with Backend (Every 30s)
  useEffect(() => {
    if (loading || submitting) return;

    const interval = setInterval(async () => {
      try {
        const liveStatus = await attemptApi.getStatus(attemptId);
        syncServerStatus(liveStatus);

        if (liveStatus.status === 'EXPIRED' || (liveStatus.seconds_remaining !== null && liveStatus.seconds_remaining <= 0)) {
          clearInterval(interval);
          handleAutoSubmit();
        } else if (liveStatus.seconds_remaining !== null) {
          setTimeRemaining(liveStatus.seconds_remaining);
        }
      } catch (err) {
        console.warn("Background status sync error:", err);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [attemptId, loading, submitting, handleAutoSubmit, setTimeRemaining, syncServerStatus]);

  // Re-synchronize when tab becomes visible or browser comes back online
  useEffect(() => {
    if (loading || submitting) return;

    const handleSyncOnResume = async () => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        try {
          const liveStatus = await attemptApi.getStatus(attemptId);
          syncServerStatus(liveStatus);

          if (liveStatus.status === 'EXPIRED' || (liveStatus.seconds_remaining !== null && liveStatus.seconds_remaining <= 0)) {
            handleAutoSubmit();
          } else if (liveStatus.seconds_remaining !== null) {
            setTimeRemaining(liveStatus.seconds_remaining);
          }
        } catch (err) {
          console.warn("Visibility resume sync error:", err);
        }
      }
    };

    document.addEventListener("visibilitychange", handleSyncOnResume);
    window.addEventListener("online", handleSyncOnResume);

    return () => {
      document.removeEventListener("visibilitychange", handleSyncOnResume);
      window.removeEventListener("online", handleSyncOnResume);
    };
  }, [attemptId, loading, submitting, handleAutoSubmit, setTimeRemaining, syncServerStatus]);

  // Local 1-second Countdown for Smooth Display
  useEffect(() => {
    if (loading || submitting || timeRemainingSeconds === null) return;

    const timer = setInterval(() => {
      tickTimer();
      if (timeRemainingSeconds <= 1) {
        clearInterval(timer);
        handleAutoSubmit();
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [loading, submitting, timeRemainingSeconds, tickTimer, handleAutoSubmit]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(e => console.error(e));
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  };

  const handleSubmitClick = () => {
    handleAutoSubmit();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 space-y-4">
        <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
        <h2 className="text-lg font-semibold text-foreground">Loading Secure Exam Session...</h2>
        <p className="text-sm text-muted-foreground">Starting server-authoritative timer and synchronizing test data.</p>
      </div>
    );
  }

  if (error && questions.length === 0) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 p-6">
        <div className="max-w-md w-full p-8 rounded-2xl border border-red-200 dark:border-red-900 bg-white dark:bg-slate-900 shadow-xl text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
          <h2 className="text-xl font-bold text-foreground">Exam Session Error</h2>
          <p className="text-sm text-muted-foreground">{error}</p>
          <div className="pt-2 flex justify-center gap-3">
            <Button onClick={() => window.location.reload()} className="glass-button">
              Retry
            </Button>
            <Button onClick={() => router.push('/mock-tests')} variant="outline">
              Back to Tests
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const currentQ = questions[currentQuestionIndex];
  if (!currentQ) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <p className="text-muted-foreground">No questions found in this mock test.</p>
      </div>
    );
  }

  const currentAnswer = answers[currentQ.id];
  const isLowTime = timeRemainingSeconds !== null && timeRemainingSeconds < 300;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 dark:bg-slate-950 select-none overflow-hidden">
      {/* Exam Header */}
      <header className="h-14 border-b border-slate-200 dark:border-slate-800 bg-slate-900 text-white flex items-center justify-between px-4 md:px-6 shrink-0 z-20">
        <div className="flex items-center gap-3">
          <span className="font-bold tracking-tight text-white flex items-center gap-2 text-sm sm:text-base">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            {test?.title || "RRB ALP CBT Mock Test"}
          </span>
        </div>

        <div className="flex items-center gap-3 sm:gap-6 text-sm">
          {/* Autosave Status Indicator */}
          <div className="hidden sm:flex items-center gap-2 text-xs font-medium">
            {saveStatus === 'saving' && (
              <span className="flex items-center gap-1 text-amber-400 animate-pulse">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving...
              </span>
            )}
            {saveStatus === 'saved' && (
              <span className="flex items-center gap-1 text-emerald-400">
                <Check className="w-3.5 h-3.5" /> Saved
              </span>
            )}
            {saveStatus === 'error' && (
              <span className="flex items-center gap-1 text-red-400" title="Will automatically retry on next action">
                <AlertCircle className="w-3.5 h-3.5" /> Retrying save...
              </span>
            )}
          </div>

          {/* Authoritative Server Countdown */}
          <div className={`flex items-center gap-2 px-3 py-1 rounded border ${isLowTime ? 'bg-red-950/50 border-red-500/50 text-red-400' : 'bg-slate-800 border-slate-700 text-slate-200'}`}>
             <Clock className={`w-4 h-4 ${isLowTime ? 'animate-pulse' : ''}`} />
             <span className="font-mono font-medium tracking-wider">{timeRemainingSeconds !== null ? formatTime(timeRemainingSeconds) : '--:--'}</span>
          </div>

          <button onClick={toggleFullscreen} className="p-2 hover:bg-slate-800 rounded hidden md:block" title="Toggle Fullscreen">
            {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
          </button>
          <button className="md:hidden p-2 hover:bg-slate-800 rounded" onClick={() => setShowPalette(!showPalette)}>
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Submission error banner if any */}
      {error && (
        <div className="bg-red-500/10 border-b border-red-500/20 text-red-600 dark:text-red-400 px-6 py-2 text-xs flex items-center justify-between">
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={() => setError(null)} className="h-6 text-xs px-2">Dismiss</Button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden relative">
        {/* Main Content Area */}
        <main className="flex-1 flex flex-col min-w-0">
          
          {/* Question Header */}
          <div className="h-12 border-b border-slate-200 dark:border-slate-800 glass-panel flex items-center px-6 shrink-0 justify-between">
            <span className="font-bold text-lg text-slate-800 dark:text-slate-100">Question {currentQuestionIndex + 1}</span>
            <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium">
               <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-foreground uppercase text-xs font-semibold">
                 {currentQ.difficulty}
               </span>
               <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800 text-xs font-semibold">
                 Marks: +1, -0.33
               </span>
            </div>
          </div>

          {/* Question Body */}
          <div className="flex-1 overflow-y-auto p-6 md:p-8 glass-panel">
            <div className="max-w-3xl">
              <div className="text-lg text-foreground mb-8 leading-relaxed font-medium">
                {currentQ.text}
              </div>
              
              <div className="space-y-3">
                {currentQ.options.map((opt, optIdx) => {
                  const isSelected = currentAnswer?.selectedOptionId === opt.id || 
                    toSelectedAnswer(currentAnswer?.selectedOptionId, currentQ.options) === toSelectedAnswer(opt.id, currentQ.options);
                  
                  return (
                    <label 
                      key={opt.id || optIdx}
                      className={`flex items-start p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                        isSelected 
                          ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/30' 
                          : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300 hover:bg-slate-50 dark:hover:bg-slate-900/50'
                      }`}
                    >
                      <input 
                        type="radio" 
                        name={`question-option-${currentQ.id}`}
                        className="sr-only"
                        checked={isSelected}
                        onChange={() => setAnswer(
                          currentQ.id, 
                          opt.id, 
                          currentAnswer?.status === 'MARKED' || currentAnswer?.status === 'ANSWERED_AND_MARKED' 
                            ? 'ANSWERED_AND_MARKED' 
                            : 'ANSWERED',
                          currentQ.options
                        )}
                      />
                      <div className="flex items-center justify-center w-6 h-6 rounded-full border border-slate-300 dark:border-slate-600 mr-4 shrink-0 shadow-sm overflow-hidden mt-0.5">
                        {isSelected && <div className="w-3 h-3 bg-indigo-600 rounded-full" />}
                      </div>
                      <span className="text-base text-foreground font-medium pt-0.5">{opt.text}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="h-16 border-t border-slate-200 dark:border-slate-800 glass-panel flex items-center px-4 md:px-6 justify-between shrink-0 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                onClick={() => {
                  const isCurrentlyMarked = currentAnswer?.status === 'MARKED' || currentAnswer?.status === 'ANSWERED_AND_MARKED';
                  const hasSelection = Boolean(currentAnswer?.selectedOptionId);
                  const newStatus = isCurrentlyMarked 
                    ? (hasSelection ? 'ANSWERED' : 'UNANSWERED')
                    : (hasSelection ? 'ANSWERED_AND_MARKED' : 'MARKED');

                  setAnswer(
                    currentQ.id, 
                    currentAnswer?.selectedOptionId, 
                    newStatus,
                    currentQ.options
                  );
                }}
                className={`hidden sm:flex border-purple-200 dark:border-purple-900 ${
                  currentAnswer?.status === 'MARKED' || currentAnswer?.status === 'ANSWERED_AND_MARKED'
                    ? 'bg-purple-100 dark:bg-purple-900/60 text-purple-900 dark:text-purple-100 font-semibold'
                    : 'text-purple-700 dark:text-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950/40'
                }`}
              >
                <Bookmark className="w-4 h-4 mr-2" /> Mark for Review
              </Button>
              <Button 
                variant="outline" 
                onClick={() => clearAnswer(currentQ.id)}
                disabled={!currentAnswer?.selectedOptionId}
                className="text-slate-600 dark:text-slate-400"
              >
                Clear Response
              </Button>
            </div>
            
            <div className="flex gap-2">
              <Button 
                variant="secondary" 
                onClick={() => setCurrentQuestion(Math.max(0, currentQuestionIndex - 1))}
                disabled={currentQuestionIndex === 0}
              >
                Previous
              </Button>
              <Button 
                className="glass-button min-w-[120px]"
                disabled={submitting}
                onClick={() => {
                  if (currentAnswer?.selectedOptionId && currentAnswer.status !== 'ANSWERED_AND_MARKED') {
                    setAnswer(currentQ.id, currentAnswer.selectedOptionId, 'ANSWERED', currentQ.options);
                  }
                  if (currentQuestionIndex < questions.length - 1) {
                    setCurrentQuestion(currentQuestionIndex + 1);
                  } else {
                    handleSubmitClick();
                  }
                }}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Submitting...
                  </>
                ) : currentQuestionIndex < questions.length - 1 ? (
                  'Save & Next'
                ) : (
                  'Submit Exam'
                )}
              </Button>
            </div>
          </div>
        </main>

        {/* Question Palette Sidebar */}
        <aside className={`
          fixed md:relative top-14 md:top-0 right-0 h-[calc(100vh-3.5rem)] md:h-auto 
          w-72 bg-slate-50 dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 flex flex-col shadow-xl md:shadow-none transition-transform z-10
          ${showPalette ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}
        `}>
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 shrink-0">
             <div className="grid grid-cols-2 gap-2 text-xs font-medium">
               <div className="flex items-center gap-2"><span className="w-5 h-5 rounded flex items-center justify-center bg-emerald-500 text-white shadow-sm">{Object.values(answers).filter(a => a.status === 'ANSWERED').length}</span> Answered</div>
               <div className="flex items-center gap-2"><span className="w-5 h-5 rounded flex items-center justify-center bg-red-500 text-white shadow-sm">{Object.values(answers).filter(a => a.status === 'UNANSWERED').length}</span> Not Answered</div>
               <div className="flex items-center gap-2"><span className="w-5 h-5 rounded flex items-center justify-center bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 shadow-sm">{questions.length - Object.keys(answers).length}</span> Not Visited</div>
               <div className="flex items-center gap-2"><span className="w-5 h-5 rounded flex items-center justify-center bg-purple-500 text-white shadow-sm">{Object.values(answers).filter(a => a.status === 'MARKED').length}</span> Marked</div>
               <div className="flex items-center gap-2 col-span-2"><span className="w-5 h-5 rounded flex items-center justify-center bg-purple-500 text-white shadow-sm relative"><span className="absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-emerald-400"></span></span> Answered & Marked</div>
             </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
             <div className="font-semibold text-sm text-foreground mb-3">Question Palette</div>
             <div className="grid grid-cols-5 gap-2">
               {questions.map((q, i) => {
                 const status = answers[q.id]?.status || 'NOT_VISITED';
                 
                 let bgClass = "bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-transparent hover:bg-slate-300";
                 let dot = null;

                 if (status === 'ANSWERED') bgClass = "bg-emerald-500 text-white border-transparent hover:bg-emerald-600 shadow-sm";
                 else if (status === 'UNANSWERED') bgClass = "bg-red-500 text-white border-transparent hover:bg-red-600 shadow-sm";
                 else if (status === 'MARKED') bgClass = "bg-purple-500 text-white border-transparent hover:bg-purple-600 shadow-sm";
                 else if (status === 'ANSWERED_AND_MARKED') {
                   bgClass = "bg-purple-500 text-white border-transparent hover:bg-purple-600 shadow-sm relative";
                   dot = <span className="absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm"></span>;
                 }

                 const isCurrent = currentQuestionIndex === i;

                 return (
                   <button
                     key={q.id}
                     type="button"
                     onClick={() => {
                        setCurrentQuestion(i);
                        if (typeof window !== 'undefined' && window.innerWidth < 768) setShowPalette(false);
                     }}
                     className={`
                       w-full aspect-square rounded flex items-center justify-center text-sm font-bold transition-all border-2
                       ${bgClass}
                       ${isCurrent ? 'ring-2 ring-offset-1 ring-slate-800 dark:ring-slate-200 !border-slate-800 dark:!border-slate-200' : ''}
                     `}
                   >
                     {i + 1}
                     {dot}
                   </button>
                 );
               })}
             </div>
          </div>
          
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900 shrink-0">
             <Button 
               variant="outline" 
               className="w-full border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-foreground font-semibold"
               onClick={handleSubmitClick}
               disabled={submitting}
             >
               {submitting ? 'Submitting...' : 'Submit Exam'}
             </Button>
          </div>
        </aside>

        {/* Mobile overlay */}
        {showPalette && (
          <div 
            className="fixed inset-0 bg-slate-900/20 z-0 md:hidden"
            onClick={() => setShowPalette(false)}
          />
        )}
      </div>
    </div>
  );
}
