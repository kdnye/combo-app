export type AppConfig = {
  quoteToolUrl: string;
  expenseToolUrl: string;
  hanaToolUrl: string;
  features: {
    hana: boolean;
  };
  preferences: {
    openLinksInNewTab: boolean;
  };
  auth: {
    enabled: boolean;
    tenantId: string | null;
    clientId: string | null;
    redirectUri: string | null;
  };
};

const truthyValues = ['1', 'true', 'yes', 'on'];

const readEnv = (env: NodeJS.ProcessEnv, key: string): string | undefined => env[key];

const readBoolean = (env: NodeJS.ProcessEnv, key: string, fallback = false): boolean => {
  const value = readEnv(env, key);
  if (typeof value !== 'string') {
    return fallback;
  }
  return truthyValues.includes(value.toLowerCase());
};

export const createAppConfig = (env: NodeJS.ProcessEnv = process.env): AppConfig => ({
  quoteToolUrl: readEnv(env, 'NEXT_PUBLIC_QUOTE_TOOL_URL') ?? 'https://quote.freightservices.net',
  expenseToolUrl:
    readEnv(env, 'NEXT_PUBLIC_EXPENSE_TOOL_URL') ?? 'https://expenses.freightservices.net',
  hanaToolUrl: readEnv(env, 'NEXT_PUBLIC_HANA_TOOL_URL') ?? 'https://mizuho.freightservices.net',
  features: {
    hana: readBoolean(env, 'NEXT_PUBLIC_FEATURE_HANA', false)
  },
  preferences: {
    openLinksInNewTab: readBoolean(env, 'NEXT_PUBLIC_OPEN_LINKS_NEW_TAB', false)
  },
  auth: {
    enabled: readBoolean(env, 'AUTH_ENABLED', false),
    tenantId: readEnv(env, 'AZURE_AD_TENANT_ID') ?? null,
    clientId: readEnv(env, 'AZURE_AD_CLIENT_ID') ?? null,
    redirectUri: readEnv(env, 'AZURE_AD_REDIRECT_URI') ?? null
  }
});

export const appConfig = createAppConfig();
