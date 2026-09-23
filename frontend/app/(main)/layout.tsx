"use client";

import Link from 'next/link';
import { LayoutDashboard, FileText, Database, Upload, BarChart3, Settings, UserCircle, BookOpen, LogOut } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';
import { useAuth } from '@/hooks/use-auth';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/mock-tests', label: 'Mock Tests', icon: FileText },
    { href: '/question-bank', label: 'Question Bank', icon: Database },
    { href: '/mistakes', label: 'Mistake Book', icon: BookOpen },
    { href: '/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/upload', label: 'Upload PDF', icon: Upload },
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row relative">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-64 flex-col glass-panel h-screen sticky top-0 border-r border-slate-200 dark:border-slate-800 z-20">
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-200 dark:border-slate-800 bg-black/5 dark:bg-white/5">
          <Link href="/dashboard" className="text-xl font-bold text-blue-600 dark:text-blue-400 tracking-tight text-glow">
            ALP<span className="text-foreground">Prep</span>
          </Link>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-black/5 dark:hover:bg-white/10 hover:text-foreground transition-all border border-transparent"
              >
                <Icon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-black/5 dark:bg-white/5 flex flex-col gap-2">
          {user && (
            <div className="px-3 py-2 flex items-center gap-2 text-xs text-muted-foreground truncate border-b border-slate-200 dark:border-slate-800 pb-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
              <span className="truncate font-medium text-foreground">{user.name || user.email}</span>
            </div>
          )}
          <div className="flex items-center justify-between px-3 py-2">
            <span className="text-sm font-medium text-slate-600 dark:text-slate-300">Theme</span>
            <ThemeToggle />
          </div>
          <Link href="/profile" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-black/5 dark:hover:bg-white/10 hover:text-foreground transition-all border border-transparent">
            <UserCircle className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Profile
          </Link>
          <Link href="/settings" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-black/5 dark:hover:bg-white/10 hover:text-foreground transition-all border border-transparent">
            <Settings className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Settings
          </Link>
          <button 
            onClick={() => logout()}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 transition-all border border-transparent text-left w-full"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-screen w-full relative z-10">
        {/* Mobile Header */}
        <header className="md:hidden h-16 border-b border-slate-200 dark:border-slate-800 glass-panel flex items-center px-4 justify-between shrink-0 sticky top-0 z-30">
          <Link href="/dashboard" className="text-lg font-bold text-blue-600 dark:text-blue-400 tracking-tight text-glow">
            ALP<span className="text-foreground">Prep</span>
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link href="/profile" className="p-2 text-slate-600 dark:text-slate-300">
              <UserCircle className="w-6 h-6" />
            </Link>
            <button onClick={() => logout()} className="p-2 text-red-500" title="Sign Out">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* Mobile Navigation */}
        <div className="md:hidden border-b border-slate-200 dark:border-slate-800 glass-panel overflow-x-auto sticky top-16 z-20 no-scrollbar shrink-0">
           <div className="flex px-4 py-3 space-x-3">
             {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="whitespace-nowrap px-4 py-2 rounded-full glass border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-foreground transition-all"
                >
                  {item.label}
                </Link>
             ))}
           </div>
        </div>
        
        <div className="flex-1 overflow-auto p-4 md:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
