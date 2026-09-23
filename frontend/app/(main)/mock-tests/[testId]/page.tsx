"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { mockTestApi, attemptApi } from "@/lib/api/services";
import { useParams, useRouter } from "next/navigation";
import { MockTest } from "@/types";
import { Play, Clock, FileText, Settings2, AlertCircle, Loader2 } from "lucide-react";

export default function MockTestDetailsPage() {
  const params = useParams();
  const testId = params.testId as string;
  const router = useRouter();
  const [test, setTest] = useState<MockTest | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    mockTestApi.getById(testId).then(res => {
      setTest(res.test);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setError(err?.message || "Failed to load test details");
      setLoading(false);
    });
  }, [testId]);

  const handleStart = async () => {
    if (!test) return;
    setStarting(true);
    setError(null);
    try {
      const attempt = await attemptApi.create(test.id);
      router.push(`/exam/${attempt.id}`);
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Failed to create attempt. Please retry.");
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
        <p className="text-muted-foreground">Loading test details...</p>
      </div>
    );
  }

  if (!test) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
        <h3 className="text-lg font-semibold text-foreground">Test Not Found</h3>
        <p className="text-muted-foreground">{error || "Could not locate this test."}</p>
        <Button onClick={() => router.push('/mock-tests')} variant="outline">
          Back to Tests
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">{test.title}</h1>
        <p className="text-muted-foreground mt-1">Ready for your test?</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Test Information</CardTitle>
          <CardDescription>Review the rules and configuration before starting.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 text-sm border border-red-200 dark:border-red-900">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
             <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 flex flex-col items-center justify-center text-center">
               <Clock className="w-6 h-6 text-indigo-500 mb-2" />
               <span className="text-sm font-medium text-muted-foreground">Duration</span>
               <span className="text-lg font-semibold text-foreground">{test.durationMinutes || 60} mins</span>
             </div>
             <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 flex flex-col items-center justify-center text-center">
               <FileText className="w-6 h-6 text-indigo-500 mb-2" />
               <span className="text-sm font-medium text-muted-foreground">Questions</span>
               <span className="text-lg font-semibold text-foreground">{test.totalQuestions}</span>
             </div>
             <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 flex flex-col items-center justify-center text-center">
               <Settings2 className="w-6 h-6 text-indigo-500 mb-2" />
               <span className="text-sm font-medium text-muted-foreground">Negative Marks</span>
               <span className="text-lg font-semibold text-foreground">1/3rd</span>
             </div>
             <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 flex flex-col items-center justify-center text-center">
               <AlertCircle className="w-6 h-6 text-indigo-500 mb-2" />
               <span className="text-sm font-medium text-muted-foreground">Auto Submit</span>
               <span className="text-lg font-semibold text-foreground">Yes</span>
             </div>
          </div>

          <div>
             <h3 className="text-sm font-semibold text-foreground mb-3">Subjects Included</h3>
             <div className="flex flex-wrap gap-2">
               {(test.subjects || []).map(sub => (
                 <span key={sub} className="px-3 py-1 bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 rounded-full text-xs font-medium border border-indigo-100 dark:border-indigo-800">
                   {sub}
                 </span>
               ))}
             </div>
          </div>
        </CardContent>
        <CardFooter className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-6 flex justify-between items-center">
          <p className="text-sm text-muted-foreground">The backend timer is authoritative.</p>
          <Button 
            onClick={handleStart} 
            disabled={starting}
            size="lg"
            className="glass-button"
          >
            {starting ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" /> Starting...
              </>
            ) : (
              <>
                <Play className="w-5 h-5 mr-2" /> Start Attempt
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
