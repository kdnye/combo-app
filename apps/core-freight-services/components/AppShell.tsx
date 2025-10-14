import { type ReactNode } from 'react';
import { appConfig } from '@/config';
import { PreferencesProvider } from '@/components/preferences/preferences-provider';
import { AuthProvider } from '@/components/auth/auth-provider';
import { BrandLogo } from '@/components/BrandLogo';
import { Button } from '@/components/ui/button';
import { TopNav } from '@/components/navigation/TopNav';

const navLinks = [
  { href: '/', label: 'Dashboard' },
  { href: '/settings', label: 'Settings' }
];

type ShellContainerProps = {
  children: ReactNode;
};

const ShellContainer = ({ children }: ShellContainerProps) => (
  <div className="flex min-h-screen flex-col bg-background">
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-6 px-6 py-5">
        <div className="flex items-center gap-4">
          <BrandLogo className="h-12 w-12" size={48} />
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Core Freight Services</p>
            <h1 className="text-2xl font-semibold text-foreground">Core Freight Services</h1>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <TopNav links={navLinks} />
          <Button aria-label="User menu placeholder" className="hidden sm:inline-flex" variant="outline">
            User
          </Button>
        </div>
      </div>
    </header>
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
    <footer className="border-t border-slate-200 bg-white/70">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4 text-xs text-muted">
        <span>© {new Date().getFullYear()} Freight Services International</span>
        <span>All rights reserved.</span>
      </div>
    </footer>
  </div>
);

type AppShellProps = {
  children: ReactNode;
};

export const AppShell = ({ children }: AppShellProps) => {
  const shell = (
    <PreferencesProvider>
      <ShellContainer>{children}</ShellContainer>
    </PreferencesProvider>
  );

  if (appConfig.auth.enabled) {
    return <AuthProvider>{shell}</AuthProvider>;
  }

  return shell;
};
