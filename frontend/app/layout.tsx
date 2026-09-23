import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/theme-provider';

export const metadata: Metadata = {
  title: 'RRB ALP Mock Test Platform',
  description: 'A premium, modern RRB ALP CBT preparation platform frontend.',
  openGraph: {
    title: 'RRB ALP Mock Test Platform',
    description: 'A premium, modern RRB ALP CBT preparation platform frontend.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'RRB ALP Mock Test Platform',
    description: 'A premium, modern RRB ALP CBT preparation platform frontend.',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
