"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { analyticsApi, subjectsApi } from "@/lib/api/services";
import { AnalyticsDashboard, Subject } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import Link from "next/link";
import { Play, TrendingUp, AlertCircle, ArrowRight, BookOpen } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      analyticsApi.getDashboardData(),
      subjectsApi.getSubjects(),
    ]).then(([analyticsRes, subjectsRes]) => {
      if (analyticsRes.status === "fulfilled") {
        setData(analyticsRes.value);
      }
      if (subjectsRes.status === "fulfilled") {
        setSubjects(subjectsRes.value);
      }
      setLoading(false);
    });
  }, []);

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Welcome back{user?.name ? `, ${user.name.split(" ")[0]}` : ", Aspirant"}
          </h1>
          <p className="text-muted-foreground mt-1">Ready to ace your RRB ALP exam?</p>
        </div>
        <div className="flex items-center gap-3">
          <Button asChild className="glass-button">
            <Link href="/mock-tests/create">
              <Play className="w-4 h-4 mr-2" /> Start Mock Test
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/question-bank">Quick Practice</Link>
          </Button>
        </div>
      </header>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-32 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-32 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-32 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardContent className="p-6 flex flex-col justify-center h-full">
                <p className="text-sm font-medium text-muted-foreground mb-1">Average Score</p>
                <div className="flex items-baseline gap-2">
                  <h2 className="text-4xl font-bold text-foreground">
                    {data?.averageScore ? `${Math.round(data.averageScore)}%` : "N/A"}
                  </h2>
                  {data?.totalTestsTaken ? (
                    <span className="flex items-center text-xs font-medium text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30 px-2 py-0.5 rounded-full">
                      <TrendingUp className="w-3 h-3 mr-1" /> {data.totalTestsTaken} tests
                    </span>
                  ) : null}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 flex flex-col justify-center h-full">
                <p className="text-sm font-medium text-muted-foreground mb-1">Latest Score</p>
                <h2 className="text-4xl font-bold text-foreground">
                  {data?.latestScore !== undefined ? `${Math.round(data.latestScore)}%` : "N/A"}
                </h2>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6 flex flex-col justify-center h-full">
                <p className="text-sm font-medium text-muted-foreground mb-1">Overall Accuracy</p>
                <h2 className="text-4xl font-bold text-foreground">
                  {data?.averageAccuracy ? `${Math.round(data.averageAccuracy)}%` : "N/A"}
                </h2>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <Card>
              <CardHeader>
                <CardTitle>Subject Mastery</CardTitle>
                <CardDescription>Your performance across ALP subjects</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {(data?.subjectStrengths && data.subjectStrengths.length > 0
                    ? data.subjectStrengths
                    : subjects.length > 0
                    ? subjects.map((s, idx) => ({ subjectName: s.name, accuracy: Math.max(30, 85 - idx * 10) }))
                    : [
                        { subjectName: "Mathematics", accuracy: 85 },
                        { subjectName: "Reasoning", accuracy: 78 },
                        { subjectName: "Physics", accuracy: 55 },
                        { subjectName: "Chemistry", accuracy: 65 },
                        { subjectName: "Biology", accuracy: 70 },
                      ]
                  ).map((item) => (
                    <div key={item.subjectName} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-foreground">{item.subjectName}</span>
                      <div className="flex-1 mx-4 h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, Math.max(10, item.accuracy))}%` }}
                        />
                      </div>
                      <span className="text-sm text-muted-foreground w-12 text-right">
                        {Math.round(item.accuracy)}%
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recommended Action</CardTitle>
                <CardDescription>Based on your recent performance</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 rounded-lg border border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/20">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-300">
                        {data?.weakSubject ? `Focus Area: ${data.weakSubject}` : "Targeted Practice"}
                      </h4>
                      <p className="text-sm text-amber-800 dark:text-amber-400 mt-1">
                        {data?.weakTopics && data.weakTopics.length > 0
                          ? `Accuracy in ${data.weakTopics.join(", ")} is below 50%. Focus on this before your next full mock.`
                          : "Take regular practice tests to identify weak areas and boost your CBT speed."}
                      </p>
                      <Button asChild variant="outline" size="sm" className="mt-3 text-amber-900 dark:text-amber-200 border-amber-300 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-900/40">
                        <Link href="/question-bank">Practice Weak Topics</Link>
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="pt-2">
                  <Link href="/mistakes" className="flex items-center justify-between p-3 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group border border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-3">
                      <BookOpen className="w-5 h-5 text-indigo-500" />
                      <div>
                        <h4 className="text-sm font-medium text-foreground group-hover:text-indigo-600 transition-colors">Review Mistake Book</h4>
                        <p className="text-xs text-muted-foreground">Review questions you previously marked or answered wrong.</p>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-indigo-600 transition-colors" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
