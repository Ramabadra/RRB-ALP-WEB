"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { mockTestApi, subjectsApi } from "@/lib/api/services";
import { useRouter } from "next/navigation";
import { MockTestConfig, Subject } from "@/types";
import { Loader2 } from "lucide-react";

export default function CreateMockTestPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [availableSubjects, setAvailableSubjects] = useState<Subject[]>([]);
  
  const [config, setConfig] = useState<MockTestConfig>({
    questionCount: 75,
    subjects: ['Mathematics', 'Reasoning', 'Physics', 'Chemistry', 'Biology'],
    difficulty: 'Mixed',
    source: 'Mixed'
  });

  useEffect(() => {
    subjectsApi.getSubjects().then(subs => {
      if (subs && subs.length > 0) {
        setAvailableSubjects(subs);
        setConfig(prev => ({
          ...prev,
          subjects: subs.map(s => s.name || s.id),
        }));
      }
    }).catch(console.error);
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const test = await mockTestApi.generate(config);
      router.push(`/mock-tests/${test.id}`);
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Failed to generate mock test. Please check backend connection.");
      setLoading(false);
    }
  };

  const subjectNames = availableSubjects.length > 0 
    ? availableSubjects.map(s => s.name)
    : ['Mathematics', 'Reasoning', 'Physics', 'Chemistry', 'Biology'];

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Create Mock Test</h1>
        <p className="text-muted-foreground mt-1">Configure your practice session.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>Select parameters to generate a custom test</CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          {error && (
            <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 text-sm border border-red-200 dark:border-red-900">
              {error}
            </div>
          )}

          {/* Question Count */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Question Count</h3>
            <div className="flex flex-wrap gap-3">
              {[20, 30, 40, 50, 75].map(num => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setConfig({ ...config, questionCount: num })}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    config.questionCount === num 
                      ? 'bg-indigo-600 text-white shadow-sm' 
                      : 'border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {num} Questions
                </button>
              ))}
            </div>
          </div>

          {/* Subjects */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Subjects</h3>
            <div className="flex flex-wrap gap-3">
              {subjectNames.map(sub => {
                const isSelected = config.subjects.includes(sub);
                return (
                  <button
                    key={sub}
                    type="button"
                    onClick={() => {
                      if (isSelected && config.subjects.length > 1) {
                        setConfig({ ...config, subjects: config.subjects.filter(s => s !== sub) });
                      } else if (!isSelected) {
                        setConfig({ ...config, subjects: [...config.subjects, sub] });
                      }
                    }}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      isSelected 
                        ? 'bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800' 
                        : 'border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                  >
                    {sub}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Difficulty */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Difficulty</h3>
              <div className="flex flex-wrap gap-3">
                {['Easy', 'Medium', 'Hard', 'Mixed'].map(diff => (
                  <button
                    key={diff}
                    type="button"
                    onClick={() => setConfig({ ...config, difficulty: diff as any })}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      config.difficulty === diff 
                        ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 shadow-sm' 
                        : 'border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                  >
                    {diff}
                  </button>
                ))}
              </div>
            </div>

            {/* Source */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Question Source</h3>
              <div className="flex flex-wrap gap-3">
                {['PYQ Only', 'AI Generated', 'Mixed'].map(src => (
                  <button
                    key={src}
                    type="button"
                    onClick={() => setConfig({ ...config, source: src as any })}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      config.source === src 
                        ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 shadow-sm' 
                        : 'border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                  >
                    {src}
                  </button>
                ))}
              </div>
            </div>
          </div>

        </CardContent>
        <CardFooter className="bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-6">
          <Button 
            onClick={handleGenerate} 
            disabled={loading}
            className="w-full sm:w-auto ml-auto glass-button"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating...
              </>
            ) : (
              'Generate Mock Test'
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
