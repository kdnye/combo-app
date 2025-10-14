'use client';

import Image from 'next/image';
import { usePreferences } from '@/components/preferences/preferences-provider';
import { brandTokens } from '@/design-tokens';
import { appConfig } from '@/config';

const SettingsPage = () => {
  const { openLinksInNewTab, setOpenLinksInNewTab } = usePreferences();

  return (
    <section aria-labelledby="settings-heading" className="space-y-10">
      <div>
        <h2 className="text-2xl font-semibold" id="settings-heading">
          Settings
        </h2>
        <p className="text-sm text-muted">Configure how launcher links behave and review theme assets.</p>
      </div>

      <section aria-labelledby="behavior-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-lg font-semibold" id="behavior-heading">
          Launcher behavior
        </h3>
        <div className="mt-4 flex items-center justify-between gap-4">
          <label className="flex flex-col" htmlFor="open-links-toggle">
            <span className="text-sm font-medium text-foreground">Open links in new tab</span>
            <span className="text-xs text-muted">
              Applies immediately across the dashboard. Stored locally per browser.
            </span>
          </label>
          <input
            aria-describedby="behavior-heading"
            aria-label="Toggle opening links in a new browser tab"
            checked={openLinksInNewTab}
            className="h-6 w-12 cursor-pointer appearance-none rounded-full bg-muted transition-colors before:ml-1 before:mt-[3px] before:block before:h-4 before:w-4 before:rounded-full before:bg-white before:transition-transform checked:bg-primary checked:before:translate-x-6"
            id="open-links-toggle"
            role="switch"
            type="checkbox"
            onChange={(event) => setOpenLinksInNewTab(event.target.checked)}
          />
        </div>
      </section>

      <section
        aria-labelledby="theme-heading"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
      >
        <h3 className="text-lg font-semibold" id="theme-heading">
          Theme tokens
        </h3>
        <p className="mt-2 text-xs text-muted">
          Values auto-detected from shared packages when available. Replace TODO placeholders once official tokens are published.
        </p>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          {Object.entries(brandTokens.colors).map(([token, value]) => (
            <div key={token} className="flex items-center gap-3">
              <span
                aria-hidden="true"
                className="h-8 w-8 rounded-full border"
                style={{ backgroundColor: value }}
              />
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted">{token}</dt>
                <dd className="font-mono text-sm">{value}</dd>
              </div>
            </div>
          ))}
          {Object.entries(brandTokens.fonts).map(([token, value]) => (
            <div key={token} className="sm:col-span-2">
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted">{token}</dt>
              <dd className="font-mono text-sm break-all">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-6 flex items-center gap-4">
          <div className="rounded-2xl border border-dashed border-slate-300 p-4">
            <Image alt="FSI logo" height={64} src="/brand/fsi-logo.svg" width={64} />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">Logo preview</p>
            <p className="text-xs text-muted">Source: /public/brand/fsi-logo.svg</p>
          </div>
        </div>
      </section>

      <section
        aria-labelledby="auth-heading"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
      >
        <h3 className="text-lg font-semibold" id="auth-heading">
          Azure AD (scaffold)
        </h3>
        <p className="mt-2 text-xs text-muted">
          TODO: Wire Microsoft Entra ID authentication once client ID, tenant ID, and redirect URI are finalized.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm" htmlFor="tenant-id">
            Tenant ID
            <input
              className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs"
              disabled
              id="tenant-id"
              placeholder="TODO: Provide tenant ID"
              value={appConfig.auth.tenantId ?? ''}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm" htmlFor="client-id">
            Client ID
            <input
              className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs"
              disabled
              id="client-id"
              placeholder="TODO: Provide client ID"
              value={appConfig.auth.clientId ?? ''}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm sm:col-span-2" htmlFor="redirect-uri">
            Redirect URI
            <input
              className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs"
              disabled
              id="redirect-uri"
              placeholder="TODO: Provide redirect URI"
              value={appConfig.auth.redirectUri ?? ''}
            />
          </label>
        </div>
        <p className="mt-4 text-xs text-muted">
          Set <code className="rounded bg-slate-100 px-1">AUTH_ENABLED=true</code> once configuration is ready. See documentation in auth/azure-ad.md.
        </p>
      </section>
    </section>
  );
};

export default SettingsPage;
