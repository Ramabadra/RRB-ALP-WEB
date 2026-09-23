"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { Plus, FileText, Clock, AlertCircle } from "lucide-react";
import { mockTestApi } from "@/lib/api/services";
import { MockTest } from "@/types";

export default function MockTestsPage() {
  const [tests, setTests] = useState<MockTest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    mockTestApi.list().then(res => {
      setTests(res);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Mock Tests</h1>
          <p className="text-muted-foreground mt-1">Practice with generated tests.</p>
        </div>
        <Button asChild className="glass-button">
          <Link href="/mock-tests/create">
            <Plus className="w-4 h-4 mr-2" /> Create New Test
          </Link>
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="h-48 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-48 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
          <div className="h-48 bg-slate-100 dark:bg-slate-800 animate-pulse rounded-xl" />
        </div>
      ) : tests.length === 0 ? (
        <Card className="p-8 text-center">
          <CardContent className="flex flex-col items-center justify-center space-y-4 pt-6">
            <AlertCircle className="w-10 h-10 text-muted-foreground" />
            <div className="space-y-1">
              <h3 className="text-lg font-semibold text-foreground">No Mock Tests Available</h3>
              <p className="text-sm text-muted-foreground">Generate your first custom test to begin practicing.</p>
            </div>
            <Button asChild className="glass-button">
              <Link href="/mock-tests/create">
                <Plus className="w-4 h-4 mr-2" /> Generate Mock Test
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tests.map(test => (
            <Card key={test.id} className="hover:border-indigo-300 dark:hover:border-indigo-800 transition-colors">
              <CardHeader>
                <CardTitle className="text-lg">{test.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mb-6">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    {test.durationMinutes || 60} mins
                  </div>
                  <div className="flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    {test.totalQuestions} Qs
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button asChild variant="outline" className="w-full">
                    <Link href={`/mock-tests/${test.id}`}>
                      View Details
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
