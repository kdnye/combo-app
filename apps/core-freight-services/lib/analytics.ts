export type AnalyticsEvent = {
  name: string;
  properties?: Record<string, unknown>;
};

/**
 * TODO: Wire this to the centralized telemetry pipeline (e.g., Azure App Insights).
 */
export const trackEvent = (_event: AnalyticsEvent): void => {
  if (process.env.NODE_ENV !== 'production') {
    // eslint-disable-next-line no-console
    console.debug('[analytics] trackEvent is a no-op until telemetry is implemented.');
  }
};
