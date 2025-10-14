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

const defaultRgbChannels = {
  primary: '15 23 42',
  secondary: '29 78 216',
  accent: '16 185 129',
  background: '248 250 252',
  foreground: '15 23 42',
  muted: '148 163 184'
} as const;

function toRgbChannels(color: string, fallback: string): string {
  const value = color.trim();

  if (value.startsWith('#')) {
    let hex = value.slice(1);
    if (hex.length === 3) {
      hex = hex
        .split('')
        .map((char) => char + char)
        .join('');
    }
    if (hex.length === 6) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      if ([r, g, b].every((channel) => !Number.isNaN(channel))) {
        return `${r} ${g} ${b}`;
      }
    }
  }

  const rgbMatch = value.match(/^rgba?\(([^)]+)\)$/i);
  if (rgbMatch) {
    const channelExpression = rgbMatch[1].split('/')[0];
    const channels = channelExpression
      .split(/[,\s]+/)
      .filter(Boolean)
      .slice(0, 3);
    if (channels.length === 3) {
      return channels.join(' ');
    }
  }

  return fallback;
}

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
  '--fsi-primary-rgb': toRgbChannels(brandTokens.colors.primary, defaultRgbChannels.primary),
  '--fsi-secondary': brandTokens.colors.secondary,
  '--fsi-secondary-rgb': toRgbChannels(brandTokens.colors.secondary, defaultRgbChannels.secondary),
  '--fsi-accent': brandTokens.colors.accent,
  '--fsi-accent-rgb': toRgbChannels(brandTokens.colors.accent, defaultRgbChannels.accent),
  '--fsi-bg': brandTokens.colors.background,
  '--fsi-bg-rgb': toRgbChannels(brandTokens.colors.background, defaultRgbChannels.background),
  '--fsi-fg': brandTokens.colors.foreground,
  '--fsi-fg-rgb': toRgbChannels(brandTokens.colors.foreground, defaultRgbChannels.foreground),
  '--fsi-muted': brandTokens.colors.muted,
  '--fsi-muted-rgb': toRgbChannels(brandTokens.colors.muted, defaultRgbChannels.muted),
  '--fsi-font-sans': brandTokens.fonts.sans,
  '--fsi-font-mono': brandTokens.fonts.mono
};

export type TailwindThemeExtension = {
  colors: Record<string, string>;
  fontFamily: Record<string, string>;
};

export const tailwindTheme: TailwindThemeExtension = {
  colors: {
    primary: 'rgb(var(--fsi-primary-rgb) / <alpha-value>)',
    secondary: 'rgb(var(--fsi-secondary-rgb) / <alpha-value>)',
    accent: 'rgb(var(--fsi-accent-rgb) / <alpha-value>)',
    background: 'rgb(var(--fsi-bg-rgb) / <alpha-value>)',
    foreground: 'rgb(var(--fsi-fg-rgb) / <alpha-value>)',
    muted: 'rgb(var(--fsi-muted-rgb) / <alpha-value>)'
  },
  fontFamily: {
    sans: 'var(--fsi-font-sans)',
    mono: 'var(--fsi-font-mono)'
  }
};
