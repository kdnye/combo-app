import './globals.css';
import type { Metadata } from 'next';
import { AppShell } from '@/components/AppShell';
import { brandTokens } from '@/design-tokens';

export const metadata: Metadata = {
  title: 'Core Freight Services',
  description: 'Launcher for FSI freight tooling.',
  icons: {
    icon: '/brand/favicon.ico'
  }
};

const RootLayout = ({ children }: { children: React.ReactNode }) => (
  <html lang="en" style={{ colorScheme: 'light' }}>
    <body
      style={{
        backgroundColor: brandTokens.colors.background,
        color: brandTokens.colors.foreground,
        fontFamily: 'var(--fsi-font-sans)'
      }}
    >
      <AppShell>{children}</AppShell>
    </body>
  </html>
);

export default RootLayout;
