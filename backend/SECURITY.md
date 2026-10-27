# Security assumptions and known limitations

Passing tests do not by themselves establish production security.

## Implemented in this slice (pending local test execution)

- Password hashing with Argon2; opaque session tokens are stored as SHA-256 hashes.
- Session cookies are HttpOnly and SameSite=Strict. Secure cookies are required in production.
- State-changing authenticated endpoints require a per-session CSRF token in `X-CSRF-Token`.
- Capsule ownership is part of the database query. Foreign and missing capsule IDs both return 404.
- Unlock time is computed server-side from the owner's birthday and timezone.
- Sealed capsule responses expose only ID, year, state, and unlock time.
- Disabling a user revokes active sessions.
- Login errors do not distinguish unknown, wrong-password, and disabled accounts.

## Known limitations

- Login throttling is in-process memory and is not shared across workers; replace with a shared store before production.
- IP throttling trusts the immediate request client; proxy configuration must be reviewed before deployment.
- Admin MFA is not implemented.
- Database schema creation uses SQLAlchemy `create_all` only in development; migrations are not implemented.
- Private media storage/endpoints do not exist. Media privacy is not implemented; the corresponding test is explicitly skipped.
- Admin features are limited to creating/disabling friends and creating capsules.
- Birthday unlock is 00:00 local time; February 29 birthdays unlock February 28 in non-leap years.
- Letters are JSON data; the future frontend must render their content as text, not trusted HTML.
