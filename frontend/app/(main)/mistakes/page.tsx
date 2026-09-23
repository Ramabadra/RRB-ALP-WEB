"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { mistakesApi, subjectsApi } from "@/lib/api/services";
import { MistakeQuestion, Subject } from "@/types";
import { Trash2, BookOpen, AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";

export default function MistakesPage() {
  const [mistakes, setMistakes] = useState<MistakeQuestion[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      mistakesApi.list(),
      subjectsApi.getSubjects(),
    ]).then(([mistakesRes, subjectsRes]) => {
      if (mistakesRes.status === "fulfilled") {
        setMistakes(mistakesRes.value);
      }
      if (subjectsRes.status === "fulfilled") {
        setSubjects(subjectsRes.value);
      }
      setLoading(false);
    });
  }, []);

  const handleRemove = async (id: string) => {
    try {
      await mistakesApi.remove(id);
      setMistakes(prev => prev.filter(m => m.id !== id));
    } catch (err) {
      console.error("Failed to remove mistake", err);
    }
  };

  const filtered = selectedSubject === "ALL" 
    ? mistakes 
    : mistakes.filter(m => m.question?.subjectId === selectedSubject);

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Mistake Book</h1>
          <p className="text-muted-foreground mt-1">Review and master questions you previously got wrong.</p>
        </div>
        {mistakes.length > 0 && (
          <Button asChild className="glass-button">
            <Link href="/mock-tests/create">
              Practice Mistakes
            </Link>
          </Button>
        )}
      </div>

      {/* Filter by subject */}
      {subjects.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setSelectedSubject("ALL")}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              selectedSubject === "ALL"
                ? "bg-indigo-600 text-white"
                : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200"
            }`}
          >
            All ({mistakes.length})
          </button>
          {subjects.map(s => {
            const count = mistakes.filter(m => m.question?.subjectId === s.id).length;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setSelectedSubject(s.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  selectedSubject === s.id
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200"
                }`}
              >
                {s.name} {count > 0 ? `(${count})` : ''}
              </button>
            );
          })}
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          <div className="h-36 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-36 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-12 text-center">
          <CardContent className="flex flex-col items-center justify-center space-y-3">
            <BookOpen className="w-12 h-12 text-muted-foreground" />
            <h3 className="text-lg font-semibold text-foreground">Mistake Book is Empty</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Any questions you answer incorrectly during mock tests will automatically appear here for revision.
            </p>
            <Button asChild variant="outline" className="mt-2">
              <Link href="/mock-tests">Take a Mock Test</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filtered.map(m => {
            const q = m.question;
            if (!q) return null;
            return (
              <Card key={m.id} className="border-slate-200 dark:border-slate-800">
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-base font-medium text-foreground leading-relaxed">
                      {q.text}
                    </span>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/30 shrink-0"
                      onClick={() => handleRemove(m.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm pt-2">
                    {q.options.map(opt => {
                      const isCorrect = opt.id === q.correctOptionId;
                      const isUserAnswer = opt.id === m.userAnswerId;

                      let badgeClass = "border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300";
                      if (isCorrect) {
                        badgeClass = "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 font-semibold";
                      } else if (isUserAnswer) {
                        badgeClass = "border-red-500 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300";
                      }

                      return (
                        <div key={opt.id} className={`p-3 rounded-lg border flex items-center justify-between ${badgeClass}`}>
                          <span>{opt.text}</span>
                          {isCorrect && <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold ml-2">Correct</span>}
                          {isUserAnswer && !isCorrect && <span className="text-xs text-red-600 dark:text-red-400 font-bold ml-2">Your Choice</span>}
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
            );
          })}
        </div>
      )}
    </div>
  );
}
