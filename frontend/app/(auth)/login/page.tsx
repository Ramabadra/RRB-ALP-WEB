"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { setAccessToken, setStoredUser } from "@/lib/auth/token";

export default function LoginPage() {
  const { initiateGoogleLogin, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleGoogleSignIn = async () => {
    setLoading(true);
    try {
      await initiateGoogleLogin();
    } catch {
      setLoading(false);
    }
  };

  const handleDemoBypass = () => {
    // Allows testing preview without active Render backend connection
    setAccessToken("preview-guest-token");
    setStoredUser({
      id: "preview-user-1",
      name: "Guest Aspirant",
      email: "aspirant@example.com",
    });
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative bg-slate-50 dark:bg-slate-950">
      <div className="absolute top-4 right-4 z-50">
        <ThemeToggle />
      </div>
      <Card className="w-full max-w-md glass border border-slate-200 dark:border-slate-800 shadow-xl">
        <CardHeader className="text-center pb-2">
          <CardTitle className="text-2xl font-bold tracking-tight text-foreground">
            Welcome to ALP Prep
          </CardTitle>
          <CardDescription className="text-slate-500 dark:text-muted-foreground">
            The premium RRB ALP CBT Mock Test Platform
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 space-y-4">
          <Button 
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="w-full glass-hover text-foreground border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-center gap-3 h-12 text-base font-medium"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
            )}
            Sign in with Google
          </Button>

          <div className="pt-2 text-center">
            <button
              type="button"
              onClick={handleDemoBypass}
              className="text-xs text-slate-500 dark:text-muted-foreground hover:underline transition-colors"
            >
              Or enter demo guest mode for preview
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
