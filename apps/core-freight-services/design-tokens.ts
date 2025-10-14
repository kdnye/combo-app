type BrandTokens = {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    foreground: string;
    muted: string;
  };
  fonts: {
    sans: string;
    mono: string;
  };
};

function loadExternalTokens(): Partial<BrandTokens> {
  try {
    // Attempt to load consolidated tokens if the shared package exists.
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const shared = require('@fsi/design-tokens');
    if (shared?.brandTokens) {
      return shared.brandTokens as BrandTokens;
    }
  } catch (error) {
    // no-op: shared tokens not available in this workspace yet.
  }

  try {
    // Attempt to read local sibling package tokens (monorepo scenario).
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const local = require('../../packages/design-tokens');
    if (local?.brandTokens) {
      return local.brandTokens as BrandTokens;
    }
  } catch (error) {
    // no-op: local tokens not available.
  }

  return {};
}

const externalTokens = loadExternalTokens();

export const brandTokens: BrandTokens = {
  colors: {
    primary:
      externalTokens.colors?.primary ?? '#0F172A' /* TODO: Replace with --fsi-primary */,
    secondary:
      externalTokens.colors?.secondary ?? '#1D4ED8' /* TODO: Replace with --fsi-secondary */,
    accent:
      externalTokens.colors?.accent ?? '#10B981' /* TODO: Replace with --fsi-accent */,
    background:
      externalTokens.colors?.background ?? '#F8FAFC' /* TODO: Replace with --fsi-bg */,
    foreground:
      externalTokens.colors?.foreground ?? '#0F172A' /* TODO: Replace with --fsi-fg */,
    muted:
      externalTokens.colors?.muted ?? '#94A3B8' /* TODO: Replace with --fsi-muted */
  },
  fonts: {
    sans:
      externalTokens.fonts?.sans ??
      '"Inter", "Helvetica Neue", Arial, system-ui, sans-serif' /* TODO: Replace with --fsi-font-sans */,
    mono:
      externalTokens.fonts?.mono ??
      '"JetBrains Mono", "SFMono-Regular", ui-monospace, monospace' /* TODO: Replace with --fsi-font-mono */
  }
};

export const cssVariables = {
  '--fsi-primary': brandTokens.colors.primary,
  '--fsi-secondary': brandTokens.colors.secondary,
  '--fsi-accent': brandTokens.colors.accent,
  '--fsi-bg': brandTokens.colors.background,
  '--fsi-fg': brandTokens.colors.foreground,
  '--fsi-muted': brandTokens.colors.muted,
  '--fsi-font-sans': brandTokens.fonts.sans,
  '--fsi-font-mono': brandTokens.fonts.mono
};

export type TailwindThemeExtension = {
  colors: Record<string, string>;
  fontFamily: Record<string, string>;
};

export const tailwindTheme: TailwindThemeExtension = {
  colors: {
    primary: 'var(--fsi-primary)',
    secondary: 'var(--fsi-secondary)',
    accent: 'var(--fsi-accent)',
    background: 'var(--fsi-bg)',
    foreground: 'var(--fsi-fg)',
    muted: 'var(--fsi-muted)'
  },
  fontFamily: {
    sans: 'var(--fsi-font-sans)',
    mono: 'var(--fsi-font-mono)'
  }
};
