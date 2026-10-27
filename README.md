# birthday-savepoint

A private, personalized birthday time-capsule experience for friends. Each person gets a themed digital environment and private birthday capsules, with past capsules remaining accessible to their owner and future capsules protected by server-enforced unlock rules.

## Status on this branch

The `phase1-backend` branch contains an initial backend implementation with authentication/session handling, owner-scoped capsules, server-side birthday locking, admin endpoints, and tests. **The test suite has not yet been run in a real dependency-installed environment. Do not treat this as production-ready.** The `main` branch remains documentation-only.

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

See [CLAUDE.md](./CLAUDE.md) for coding-agent instructions, security requirements, working protocol, and the first vertical slice. See [docs/PROJECT_CONTEXT.md](./docs/PROJECT_CONTEXT.md) and [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) for product context and staged implementation. Backend setup and limitations are in [backend/README.md](./backend/README.md), with security notes in [backend/SECURITY.md](./backend/SECURITY.md).

## Security note

Do not put real friends' personal details, passwords, private letters, or gift media in public source control, test fixtures, screenshots, or logs. Never rely on frontend-only hiding for private or locked content. Do not deploy this backend as production-ready until tests pass and the documented limitations are addressed.
