import { describe, expect, it } from 'vitest';
import { createAppConfig } from '@/config';

describe('createAppConfig', () => {
  it('falls back to default URLs when env vars are missing', () => {
    const config = createAppConfig({ NODE_ENV: 'test' } as NodeJS.ProcessEnv);
    expect(config.quoteToolUrl).toBe('https://quote.freightservices.net');
    expect(config.expenseToolUrl).toBe('https://expenses.freightservices.net');
  });

  it('parses boolean feature flags', () => {
    const config = createAppConfig({
      NEXT_PUBLIC_OPEN_LINKS_NEW_TAB: 'yes',
      AUTH_ENABLED: '1',
      NODE_ENV: 'test'
    } as NodeJS.ProcessEnv);

    expect(config.preferences.openLinksInNewTab).toBe(true);
    expect(config.auth.enabled).toBe(true);
  });

  it('coerces missing auth fields to null', () => {
    const config = createAppConfig({ NODE_ENV: 'test' } as NodeJS.ProcessEnv);
    expect(config.auth.tenantId).toBeNull();
    expect(config.auth.clientId).toBeNull();
    expect(config.auth.redirectUri).toBeNull();
  });
});
