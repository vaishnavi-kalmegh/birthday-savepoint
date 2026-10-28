# Birthday Savepoint frontend

## Local development

1. Start the backend from the `backend/` directory following its README.
2. From this directory, run `npm install`.
3. Run `npm run dev`; Vite proxies `/api` to `http://127.0.0.1:8000`.
4. Run `npm run typecheck`, `npm test`, and `npm run build`.

This first slice includes login, session restoration, a private memory shelf, generic sealed placeholders, and authorized letter viewing. It does not include password reset, notifications, private media, or production deployment. The CSRF token stays in application memory and is refreshed after page reload; session cookies remain HttpOnly.