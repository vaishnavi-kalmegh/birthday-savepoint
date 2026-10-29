# Birthday Savepoint frontend

## Local development

1. Start the backend from the `backend/` directory following its README.
2. From this directory, run `npm install`.
3. Run `npm run dev`; Vite proxies `/api` to `http://127.0.0.1:8000`.
4. Run `npm run typecheck`, `npm test`, and `npm run build`.

## Current slice

- Login, session restoration, logout, a private memory shelf, generic sealed placeholders, and authorized letter viewing.
- Four original CSS pixel-art scene directions: `cat-garden`, `racing-night`, `comic-rooftop`, and `moonlit-hills`. The profile's `theme.scene` selects a scene; unknown values fall back to moonlit hills.
- Admin-only setup panel for creating a friend account and attaching a letter capsule. It is shown only when the authenticated `/api/auth/me` response reports `is_admin: true`; backend admin routes independently enforce admin authorization and CSRF checks.
- New letter capsule year defaults to next year to avoid accidentally publishing a capsule that is already unlocked.
- Responsive layouts and reduced-motion support.

## Important limitations

This remains a development slice, not a production-ready service. The admin panel only lets you create one friend at a time and attach a capsule to the account just created; there is no friend directory, account recovery, private media, notification delivery, admin MFA, production audit log, or deployment setup. Passwords should be handed to friends through a separate private channel. The CSRF token stays in application memory and is refreshed after page reload; session cookies remain HttpOnly. Review backend tests and the frontend CI results before merging.
