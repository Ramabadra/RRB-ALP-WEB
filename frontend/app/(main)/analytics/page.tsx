"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { analyticsApi } from "@/lib/api/services";
import { AnalyticsDashboard } from "@/types";
import { Loader2 } from "lucide-react";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsApi.getDashboardData().then(res => {
      setData(res);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  const trendData = data?.scoreHistory && data.scoreHistory.length > 0
    ? data.scoreHistory.map((item, idx) => ({
        name: item.date || `Test ${idx + 1}`,
        score: item.score,
      }))
    : [
        { name: 'Test 1', score: 65 },
        { name: 'Test 2', score: 68 },
        { name: 'Test 3', score: 72 },
        { name: 'Test 4', score: 75 },
      ];

  const subjectData = data?.subjectStrengths && data.subjectStrengths.length > 0
    ? data.subjectStrengths.map(sub => ({
        name: sub.subjectName,
        correct: Math.round((sub.accuracy / 100) * 20),
        wrong: Math.round(((100 - sub.accuracy) / 100) * 15),
        unanswered: 5,
      }))
    : [
        { name: 'Math', correct: 18, wrong: 4, unanswered: 3 },
        { name: 'Reasoning', correct: 20, wrong: 2, unanswered: 3 },
        { name: 'Physics', correct: 12, wrong: 8, unanswered: 5 },
        { name: 'Chemistry', correct: 15, wrong: 5, unanswered: 5 },
        { name: 'Biology', correct: 14, wrong: 6, unanswered: 5 },
      ];

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Performance Analytics</h1>
        <p className="text-muted-foreground mt-1">Track your progress and mastery over time.</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-[350px] bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-[350px] bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Score Trend</CardTitle>
              <CardDescription>Your mock test scores over time</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4, fill: '#4f46e5', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Subject Distribution</CardTitle>
              <CardDescription>Aggregate accuracy across subjects</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={subjectData} margin={{ top: 5, right: 0, bottom: 5, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      cursor={{ fill: '#f1f5f9' }}
                    />
                    <Bar dataKey="correct" stackId="a" fill="#10b981" radius={[0, 0, 4, 4]} />
                    <Bar dataKey="wrong" stackId="a" fill="#ef4444" />
                    <Bar dataKey="unanswered" stackId="a" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-4 mt-4 text-xs font-medium text-muted-foreground">
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-emerald-500"></span> Correct</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-red-500"></span> Wrong</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-slate-300"></span> Unanswered</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
