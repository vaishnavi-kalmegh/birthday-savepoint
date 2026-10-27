# birthday-savepoint

A private, personalized birthday time-capsule experience for friends. Each person gets a themed digital environment and private birthday capsules, with past capsules remaining accessible to their owner and future capsules protected by server-enforced unlock rules.

## Status

Project documentation and initial planning. Application features are not implemented yet.

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

The stack is provisional until implementation begins. Do not add infrastructure solely because it appears in this list.

## Development instructions

See [CLAUDE.md](./CLAUDE.md) for coding-agent instructions, security requirements, working protocol, and the first vertical slice. See [docs/PROJECT_CONTEXT.md](./docs/PROJECT_CONTEXT.md) and [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) for product context and staged implementation.

## Security note

Do not put real friends' personal details, passwords, private letters, or gift media in public source control, test fixtures, screenshots, or logs. Never rely on frontend-only hiding for private or locked content.
