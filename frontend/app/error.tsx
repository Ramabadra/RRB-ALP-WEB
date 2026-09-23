"use client";

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 p-6 text-center">
      <div className="max-w-md w-full p-8 rounded-2xl border border-red-200 dark:border-red-900 bg-white dark:bg-slate-900 shadow-xl space-y-4">
        <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-950/50 flex items-center justify-center mx-auto text-red-600 dark:text-red-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Something went wrong</h1>
        <p className="text-sm text-muted-foreground">
          An unexpected error occurred. Please try again.
        </p>
        <div className="pt-2 flex justify-center gap-3">
          <Button onClick={() => reset()} className="glass-button">
            Try again
          </Button>
          <Button onClick={() => window.location.href = '/dashboard'} variant="outline">
            Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
