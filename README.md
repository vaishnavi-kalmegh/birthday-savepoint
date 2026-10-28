# birthday-savepoint

A private, personalized birthday time-capsule experience for friends. Each person gets a themed digital environment and private birthday capsules, with past capsules remaining accessible to their owner and future capsules protected by server-enforced unlock rules.

## Status on this branch

The `phase1-hardening` branch contains the backend foundation and privacy hardening. The `phase2-first-vertical-slice` branch adds the first React + TypeScript + Vite interface for login, a private memory shelf, sealed placeholders, and letter viewing. These changes are under review in draft PRs; check GitHub Actions for current verification status. `main` remains unchanged. This is not production-ready.

## Product goals

- Personal, atmospheric pixel-art / indie-game environments.
- Private accounts and per-person birthday capsules.
- Letters and, eventually, other gift formats such as playlists, video edits, and scrapbooks.
- Secure backend-enforced time locks and private media.
- Automated reminders only after a reliable, cost-appropriate approach is chosen.

## Intended stack

- React + TypeScript + Vite
- Python + FastAPI + Pydantic
- PostgreSQL + SQLAlchemy + Alembic
- pytest and appropriate frontend/end-to-end tests

## Development instructions

See [CLAUDE.md](./CLAUDE.md) for coding-agent instructions, security requirements, working protocol, and the first vertical slice. Frontend setup is documented in [frontend/README.md](./frontend/README.md). See [docs/PROJECT_CONTEXT.md](./docs/PROJECT_CONTEXT.md) and [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) for product context and staged implementation. Backend setup and limitations are in [backend/README.md](./backend/README.md), with security notes in [backend/SECURITY.md](./backend/SECURITY.md).

## Security note

Do not put real friends' personal details, passwords, private letters, or gift media in public source control, test fixtures, screenshots, or logs. Never rely on frontend-only hiding for private or locked content. Do not deploy this backend as production-ready until tests pass and the documented limitations are addressed.
