# Backend setup

This is a first backend-only slice. Authentication and security tests are **written but not verified** until you run them locally. The four pure date tests were reported as passing in Claude's sandbox; they have not been rerun from this repository.

## Requirements

- Python 3.12+
- pip and venv
- SQLite for local development
- PostgreSQL and a valid `postgresql+psycopg://...` URL for later deployment

## Setup and run

From the repository root:

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
# Copy .env.example to .env, then edit only local settings.
# Windows PowerShell: Copy-Item .env.example .env
# macOS/Linux: cp .env.example .env
pytest -q
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/api/health` after the health route is implemented. Until then, the API routes in this slice are the available endpoints.

## Current limitations

- No Alembic migrations yet. `create_all` is for development only and is disabled in production.
- Login throttling is in-process and resets on restart; it is not sufficient for multi-worker production.
- No media endpoints, media storage, frontend, notification delivery, or admin MFA.
- No browser/e2e checks have been run.
- Do not deploy this as production-ready authentication.
