# birthday-savepoint — Claude Code Instructions

## Project purpose
Build a private, personalized birthday time-capsule website for 10+ friends. Each friend gets a private account, a themed digital environment, and a capsule for each birthday. Capsules may contain letters, playlists, video edits, scrapbooks, or other gifts. Owners can revisit past capsules; future capsules remain inaccessible until their configured unlock moment.

This is both a personal gift project and a portfolio-quality engineering project. It should feel like a memorable indie game / digital archive, not a generic birthday template or CRUD dashboard.

## Start every session by inspecting the repository
1. Inspect the existing tree, Git status, README, package manifests, backend entrypoints, tests, migrations, and configuration.
2. Summarize what exists and what appears unfinished before editing.
3. Never assume the repository is empty. Never overwrite or delete existing work without inspecting it and explaining why the change is needed.
4. Propose the smallest useful next step. For substantial changes, explain the plan and important trade-offs before implementation.

## Preferred stack (provisional)
- Frontend: React, TypeScript strict mode, Vite.
- Backend: Python, FastAPI, Pydantic v2.
- Persistence: PostgreSQL for deployed-like development; SQLAlchemy 2.x and Alembic migrations.
- Tests: pytest for backend; frontend unit tests and browser/e2e tests when appropriate.
- Local infrastructure: Docker Compose only where useful and practical.
- Private media: storage abstraction; local development may use MinIO. Do not commit to a production provider yet.
- Notifications: provider abstraction; start with manual reminders/fallback. Add email only after checking setup, current free limits, card requirements, and costs. WhatsApp is not a first-release requirement.

Keep development and testing free where possible. Before introducing a paid service, required payment method, billable usage, or material recurring cost, explain alternatives and ask for approval. Do not assume a free tier is permanently free or available without a card. Design for deployment, but do not choose a hosting provider without discussing trade-offs.

## Product and design direction
- Visual identity: atmospheric, detailed pixel-art / indie-game environment, retro digital archive, cinematic night scenes, restrained typography, smooth purposeful animations.
- Avoid generic birthday cakes/balloons, stock-template layouts, generic SaaS styling, emojis in the UI, excessive neon/glassmorphism, and decorative interactions that do nothing.
- Each theme must affect the scene, interaction, motion, typography, and capsule presentation, not only the background color.
- Personalization must be data-driven so new friends and themes can be added without duplicating the whole application.
- Example directions: an original comic-book-inspired city rooftop for Yash; a cat-themed environment for Aditya; a motorsport-inspired scene for Kartik; a distinctly different cat scene for Diya. Use original or properly licensed art. Do not include unlicensed character art, logos, or branded assets.
- Prefer original pixel art. Initial SVG/CSS art is acceptable as a prototype if it looks intentional and its limitations are stated honestly.
- Responsive on mobile and desktop. Respect reduced-motion preferences. Ensure adequate contrast, keyboard access, focus states, and useful loading/error/empty states.
- Every visible control must work. No fake success messages or inert placeholder buttons.

## Privacy and security requirements (non-negotiable)
- Every friend can access only their own profile, capsules, and private media. Do not expose a public friend directory, total account count, or account-enumeration clues.
- Use opaque random public identifiers, but never treat an identifier as authorization.
- Enforce ownership and authorization on the server for every protected operation.
- Future capsule content and media metadata must not be returned to the browser before unlock. A locked response may include only safe metadata needed to render the lock state; never send hidden letter text, media paths, signed URLs, or gift content and rely on CSS/JS to hide it.
- Private media must not be publicly addressable. Authorize before issuing short-lived signed links or proxying content.
- Use secure password hashing (Argon2id or another justified modern password hash), rate limits, safe session handling, session expiry/revocation, HTTPS in production, secure HttpOnly SameSite cookies, CSRF protection for state-changing requests, and server-side input validation.
- Store only hashes of opaque session tokens if using database-backed sessions. Do not store plaintext passwords or session tokens.
- Protect admin routes separately. Never expose secrets in source control or logs. Use synthetic data in tests and demos, not real friends' personal information.
- Consider account recovery and initial password delivery carefully; do not send passwords in public URLs.
- Treat uncertainty about authorization or future-content exposure as a blocker until resolved.

## Birthday and time-lock rules
- Store each friend's IANA timezone and make the birthday unlock policy explicit.
- Compute unlock moments server-side, never trust the browser clock.
- Handle leap years, February 29 birthdays, timezone boundaries, daylight-saving transitions where applicable, and date changes deterministically.
- Do not silently choose a February 28 or March 1 policy for leap-day birthdays. Make the policy explicit, configurable, documented, and tested before finalizing it.
- Past capsules remain accessible only to their owner. The current capsule unlocks according to the configured policy. Future capsules remain server-locked.

## Notifications
- Notification failures must never prevent a friend from logging in or manually accessing an unlocked capsule.
- Use durable delivery records, retries, idempotency/duplicate-send prevention, and observable delivery status.
- Include a manual-reminder fallback from the first release.
- Do not build WhatsApp integration into the first release. Do not depend on an email provider until its requirements and current costs/limits are checked.

## Admin needs (later milestone)
- Create/deactivate friend accounts; manage birthdays, timezones, and theme configuration.
- Create/edit capsules, set unlock dates, and upload gift media.
- Preview a friend's environment without bypassing production authorization boundaries.
- View upcoming birthdays, notification status, and failures; retry safely and revoke sessions.
- Admin-only routes and actions must be tested.

## First complete vertical slice
Do not start by building every theme, notification channel, media format, and admin feature. First deliver one coherent, tested slice:
1. Secure login and logout.
2. One personalized, polished pixel-art environment.
3. A birthday letter capsule.
4. A future capsule locked by the backend, with no hidden content sent to the client.
5. Tests proving account isolation and lock enforcement.

Only then expand to admin tools, notifications, more themes, and additional gift formats.

## Engineering standards
- Strict TypeScript and appropriate Python typing.
- Keep presentation, domain/business logic, persistence, authentication, authorization, and notification delivery separated.
- Validate all untrusted input on the server.
- Use migrations for schema changes and environment variables for configuration.
- Keep dependencies minimal and explain non-obvious choices in plain English.
- Document local setup, prerequisites, environment variables, database setup/migrations, test commands, and deployment assumptions.
- Keep the application runnable after each increment.
- Do not leave security-critical TODOs in a feature presented as complete.

## Required tests
At minimum, build tests for:
- Unauthenticated access to protected endpoints is rejected.
- Friend A cannot read or mutate Friend B's profile, capsules, or media.
- Future capsule details and content are absent from API responses before unlock.
- A locked media asset cannot be fetched directly or through a guessed identifier.
- Admin routes reject ordinary friends.
- Session expiry and revocation take effect.
- Notification retries do not produce duplicate sends.
- Birthday unlock calculations handle timezones and February 29 according to the explicitly selected policy.

## Working protocol for each substantial task
1. Inspect relevant files and Git status.
2. State a brief plan and important trade-offs.
3. Implement one coherent increment.
4. Run relevant checks and inspect their actual output.
5. Report files changed, commands run, what passed/failed, and what remains unfinished.

Never claim a test, build, deployment, visual inspection, or integration succeeded unless it was actually run and verified. If browser rendering cannot be inspected, say so and ask the project owner to review it. Do not make unrelated rewrites.
