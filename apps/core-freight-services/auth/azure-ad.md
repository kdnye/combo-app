# Azure AD / Microsoft Entra ID Integration (Scaffold)

> TODO: Replace this scaffold once the identity platform and redirect URIs are finalized.

## Current Status
- `AUTH_ENABLED` is set to `false` by default. The UI renders without any authentication guard.
- `components/auth/auth-provider.tsx` exports a stub provider that simply renders children and logs a console reminder in development builds.

## Action Items
1. Confirm tenant ID, client ID, and redirect URI with the identity team.
2. Add MSAL.js (or the preferred Azure SDK) as a dependency and initialize it inside the `AuthProvider`.
3. Gate protected routes/components behind the signed-in state and expose sign-in/sign-out actions in the top navigation.
4. Replace the placeholder "User" button in `AppShell` with the real account menu.
5. Update environment variables in `.env.local` and deployment environments, then flip `AUTH_ENABLED=true`.

## References
- [Microsoft identity platform documentation](https://learn.microsoft.com/azure/active-directory/develop/)
- [NextAuth.js Azure AD provider](https://next-auth.js.org/providers/azure-ad) (alternative approach if we standardize on NextAuth)
