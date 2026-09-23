"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api/services";
import { Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const code = searchParams.get("code");
    const state = searchParams.get("state") || undefined;

    if (!code) {
      Promise.resolve().then(() => {
        if (isMounted) setError("No authorization code found in URL.");
      });
      return;
    }

    authApi.handleGoogleCallback(code, state)
      .then(() => {
        router.push("/dashboard");
      })
      .catch((err) => {
        console.error("OAuth callback error", err);
        if (isMounted) {
          setError(err?.message || "Failed to complete Google Sign-In.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center space-y-4 bg-slate-50 dark:bg-slate-950">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <h2 className="text-xl font-bold text-foreground">Authentication Failed</h2>
        <p className="text-muted-foreground">{error}</p>
        <Button asChild variant="outline">
          <Link href="/login">Back to Login</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center space-y-4 bg-slate-50 dark:bg-slate-950">
      <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      <p className="text-sm font-medium text-muted-foreground">Authenticating session...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    }>
      <CallbackHandler />
    </Suspense>
  );
}
