# Creating the first admin (local development only)

Run from the repository root after installing backend dependencies:

```bash
cd backend
python - <<'PY'
from getpass import getpass
from app.db import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password

Base.metadata.create_all(engine)
db = SessionLocal()
try:
    db.add(User(
        login_id="admin",
        password_hash=hash_password(getpass("Admin password: ")),
        display_name="Admin",
        birth_month=1,
        birth_day=1,
        is_admin=True,
    ))
    db.commit()
finally:
    db.close()
PY
```

Use a long, unique password. It is prompted for and is not written into a source file. This bootstrap is for local development only; production account provisioning and migrations need a separate reviewed process.
