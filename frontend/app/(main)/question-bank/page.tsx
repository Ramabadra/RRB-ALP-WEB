"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { questionsApi, subjectsApi } from "@/lib/api/services";
import { Question, Subject } from "@/types";
import { Database, Filter, Sparkles } from "lucide-react";
import Link from "next/link";

export default function QuestionBankPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string>("");
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    subjectsApi.getSubjects().then(res => {
      setSubjects(res);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    let isMounted = true;
    questionsApi.getQuestions({
      subjectId: selectedSubject || undefined,
      difficulty: selectedDifficulty || undefined,
    }).then(res => {
      if (isMounted) {
        setQuestions(res);
        setLoading(false);
      }
    }).catch(err => {
      console.error(err);
      if (isMounted) {
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [selectedSubject, selectedDifficulty]);

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Question Bank</h1>
          <p className="text-muted-foreground mt-1">Browse and practice past questions and AI-generated practice sets.</p>
        </div>
        <div className="flex gap-2">
          <Button asChild className="glass-button">
            <Link href="/upload">
              Upload PYQ PDF
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/mock-tests/create">
              <Sparkles className="w-4 h-4 mr-1 text-indigo-500" /> Start Mock
            </Link>
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Filter className="w-4 h-4" /> Filters:
        </div>

        {/* Subject filter */}
        <select
          value={selectedSubject}
          onChange={(e) => {
            setLoading(true);
            setSelectedSubject(e.target.value);
          }}
          className="text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-background text-foreground"
        >
          <option value="">All Subjects</option>
          {subjects.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        {/* Difficulty filter */}
        <select
          value={selectedDifficulty}
          onChange={(e) => {
            setLoading(true);
            setSelectedDifficulty(e.target.value);
          }}
          className="text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-background text-foreground"
        >
          <option value="">All Difficulties</option>
          <option value="EASY">Easy</option>
          <option value="MEDIUM">Medium</option>
          <option value="HARD">Hard</option>
        </select>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="h-32 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-32 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-32 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
        </div>
      ) : questions.length === 0 ? (
        <Card className="p-12 text-center">
          <CardContent className="flex flex-col items-center justify-center space-y-3">
            <Database className="w-12 h-12 text-muted-foreground" />
            <h3 className="text-lg font-semibold text-foreground">No Questions Found</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Upload PYQ PDFs or generate a mock test to populate the question bank.
            </p>
            <Button asChild className="glass-button mt-2">
              <Link href="/upload">Upload Question Paper</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {questions.map((q, idx) => (
            <Card key={q.id || idx} className="border-slate-200 dark:border-slate-800">
              <CardContent className="p-6 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wide">
                        Q{idx + 1}
                      </span>
                      {q.difficulty && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">
                          {q.difficulty}
                        </span>
                      )}
                      {q.source && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300">
                          {q.source}
                        </span>
                      )}
                    </div>
                    <p className="text-base font-medium text-foreground leading-relaxed pt-1">
                      {q.text}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm pt-2">
                  {q.options.map(opt => {
                    const isCorrect = opt.id === q.correctOptionId;
                    return (
                      <div 
                        key={opt.id} 
                        className={`p-3 rounded-lg border text-xs sm:text-sm flex items-center justify-between ${
                          isCorrect 
                            ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 font-medium' 
                            : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        <span>{opt.text}</span>
                        {isCorrect && (
                          <span className="text-[10px] bg-emerald-500 text-white px-2 py-0.5 rounded font-bold ml-2">
                            Correct Answer
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {q.explanation && (
                  <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg text-xs text-muted-foreground border border-slate-100 dark:border-slate-800">
                    <strong className="text-foreground">Explanation: </strong>
                    {q.explanation}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
