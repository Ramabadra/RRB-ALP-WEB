"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { resultsApi } from "@/lib/api/services";
import { Result } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Trophy, CheckCircle2, XCircle, Clock, BarChart2, BookOpen, AlertCircle, Loader2 } from "lucide-react";

export default function ResultsPage() {
  const params = useParams();
  const attemptId = params.attemptId as string;
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    resultsApi.getById(attemptId).then(res => {
      setResult(res);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setError(err?.message || "Failed to load attempt result");
      setLoading(false);
    });
  }, [attemptId]);

  if (loading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        <p className="text-muted-foreground font-medium">Computing authoritative score...</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
        <h3 className="text-xl font-bold text-foreground">Result Unavailable</h3>
        <p className="text-muted-foreground">{error || "Could not retrieve score for this attempt."}</p>
        <Button asChild variant="outline">
          <Link href="/dashboard">Back to Dashboard</Link>
        </Button>
      </div>
    );
  }

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  };

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Exam Performance</h1>
        <p className="text-muted-foreground mt-1">Here is your complete performance breakdown.</p>
      </div>

      {/* Main Score Banner */}
      <Card className="border-indigo-100 dark:border-indigo-950 bg-gradient-to-r from-indigo-50/50 via-white to-purple-50/50 dark:from-indigo-950/20 dark:via-slate-900 dark:to-purple-950/20 shadow-sm">
        <CardContent className="p-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
             <div className="w-20 h-20 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-200 dark:shadow-none shrink-0">
               <Trophy className="w-10 h-10" />
             </div>
             <div>
               <div className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Final Score</div>
               <div className="text-5xl font-extrabold text-foreground tracking-tight mt-1">
                 {typeof result.score === 'number' ? result.score.toFixed(2) : result.score}
                 <span className="text-xl text-muted-foreground font-normal"> / {result.maxScore || result.totalQuestions}</span>
               </div>
               <p className="text-xs text-muted-foreground mt-1">Authoritative score evaluated by backend grading service.</p>
             </div>
          </div>
          
          <div className="flex flex-wrap gap-4 w-full md:w-auto justify-start md:justify-end">
            <Button asChild className="glass-button">
              <Link href="/mistakes">
                <BookOpen className="w-4 h-4 mr-2" /> Add to Mistake Book
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/dashboard">Dashboard</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Quick Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-medium text-sm mb-1">
              <CheckCircle2 className="w-4 h-4" /> Correct
            </div>
            <div className="text-2xl font-bold text-foreground">{result.correctAnswers}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-medium text-sm mb-1">
              <XCircle className="w-4 h-4" /> Wrong
            </div>
            <div className="text-2xl font-bold text-foreground">{result.wrongAnswers}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-medium text-sm mb-1">
              <BarChart2 className="w-4 h-4" /> Accuracy
            </div>
            <div className="text-2xl font-bold text-foreground">{Math.round(result.accuracy)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-medium text-sm mb-1">
              <Clock className="w-4 h-4" /> Time Spent
            </div>
            <div className="text-2xl font-bold text-foreground">{formatDuration(result.timeSpentSeconds)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Subject-Wise Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Subject Performance</CardTitle>
          <CardDescription>Accuracy and scores per subject category</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {result.subjectPerformance.map((sub) => (
              <div key={sub.subjectName} className="space-y-2">
                <div className="flex justify-between text-sm font-medium">
                  <span className="text-foreground font-semibold">{sub.subjectName}</span>
                  <span className="text-muted-foreground">
                    {sub.correct} Correct, {sub.wrong} Wrong ({Math.round(sub.accuracy)}% Accuracy)
                  </span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden flex">
                  <div 
                    className="bg-emerald-500 h-full" 
                    style={{ width: `${sub.total > 0 ? (sub.correct / sub.total) * 100 : 0}%` }} 
                  />
                  <div 
                    className="bg-red-500 h-full" 
                    style={{ width: `${sub.total > 0 ? (sub.wrong / sub.total) * 100 : 0}%` }} 
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
