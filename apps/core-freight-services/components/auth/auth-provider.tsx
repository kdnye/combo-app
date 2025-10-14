'use client';

import { type PropsWithChildren, useEffect } from 'react';

/**
 * TODO: Replace with real Azure AD / Microsoft Entra ID provider implementation.
 * This stub prevents accidental unauthenticated access until auth is wired up.
 */
export const AuthProvider = ({ children }: PropsWithChildren) => {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.info('[AuthProvider] AUTH_ENABLED is true, but authentication is not configured yet.');
    }
  }, []);

  return <>{children}</>;
};
