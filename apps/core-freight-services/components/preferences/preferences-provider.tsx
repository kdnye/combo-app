'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from 'react';
import { appConfig } from '@/config';

const OPEN_LINKS_KEY = 'fsi-open-links-new-tab';

type PreferenceContextValue = {
  openLinksInNewTab: boolean;
  setOpenLinksInNewTab: (value: boolean) => void;
};

const PreferencesContext = createContext<PreferenceContextValue | undefined>(undefined);

type PreferencesProviderProps = {
  children: ReactNode;
};

export const PreferencesProvider = ({ children }: PreferencesProviderProps) => {
  const [openLinksInNewTab, setOpenLinksInNewTabState] = useState<boolean>(
    appConfig.preferences.openLinksInNewTab,
  );

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(OPEN_LINKS_KEY);
      if (stored) {
        setOpenLinksInNewTabState(stored === 'true');
      }
    } catch (error) {
      // Ignore storage access errors (e.g., private browsing restrictions).
    }
  }, []);

  const setOpenLinksInNewTab = useCallback((value: boolean) => {
    setOpenLinksInNewTabState(value);
    try {
      window.localStorage.setItem(OPEN_LINKS_KEY, String(value));
    } catch (error) {
      // Swallow storage errors to avoid crashing the UI.
    }
  }, []);

  const contextValue = useMemo(
    () => ({
      openLinksInNewTab,
      setOpenLinksInNewTab
    }),
    [openLinksInNewTab, setOpenLinksInNewTab],
  );

  return <PreferencesContext.Provider value={contextValue}>{children}</PreferencesContext.Provider>;
};

export const usePreferences = (): PreferenceContextValue => {
  const ctx = useContext(PreferencesContext);
  if (!ctx) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return ctx;
};
