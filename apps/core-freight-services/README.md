# Core Freight Services Launcher

A Next.js launcher that consolidates key Freight Services International tools into a single dashboard.

## Getting Started

```bash
cd apps/core-freight-services
npm install
npm run dev
```

## Environment Variables

Copy `.env.example` to `.env.local` and adjust as needed:

- `NEXT_PUBLIC_QUOTE_TOOL_URL`
- `NEXT_PUBLIC_EXPENSE_TOOL_URL`
- `NEXT_PUBLIC_OPEN_LINKS_NEW_TAB`
- `AUTH_ENABLED`
- `AZURE_AD_TENANT_ID`
- `AZURE_AD_CLIENT_ID`
- `AZURE_AD_REDIRECT_URI`

## Available Scripts

- `npm run dev` – start the development server.
- `npm run build` – build the production bundle.
- `npm run start` – run the production server.
- `npm run lint` – run ESLint.
- `npm run typecheck` – run TypeScript type checking.
- `npm run test` – execute Vitest unit tests.

## Feature Flags

- `NEXT_PUBLIC_OPEN_LINKS_NEW_TAB` sets the default behavior for tool links.

## TODOs

- Replace placeholder brand tokens once the shared design package is available.
- Implement Azure AD authentication (`auth/azure-ad.md`).
- Connect telemetry in `lib/analytics.ts` to the organization-wide analytics pipeline.
