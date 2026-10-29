# Security assumptions and known limitations

Passing tests do not by themselves establish production security.

## Implemented in the hardening branch

- Password hashing with Argon2; opaque session tokens are stored as SHA-256 hashes.
- Session cookies are HttpOnly and SameSite=Strict. Secure cookies are required in production.
- State-changing authenticated endpoints require a per-session CSRF token in `X-CSRF-Token`; safe methods do not require that header.
- Capsule ownership is part of the database query. Foreign, missing, unpublished, and locked capsule IDs return 404 from the content endpoint.
- The capsule listing returns metadata only for published, unlocked capsules. It does not reveal IDs for drafts or future capsules.
- The listing includes one generic sealed placeholder calculated from the user's birthday and timezone, not from capsule records. It has no ID and does not imply that a gift has been created.
- Unlock time is computed server-side from the owner's birthday and timezone.
- Letter payloads are limited to a title and text body; text is capped at 20,000 characters and extra fields are rejected. Theme JSON is capped at 8 KiB.
- Disabling a friend revokes active sessions. An active admin cannot disable their own account through this endpoint.
- Login errors do not distinguish unknown, wrong-password, and disabled accounts.
- Login throttle storage has a hard key cap and prunes expired attempts. It uses monotonic time for the in-process window.

## Known limitations

- Login throttling is in-process memory, not shared across workers, and its bounded eviction behavior is only a development safeguard. Replace it with a shared, reviewed store before production.
- IP throttling trusts the immediate request client; proxy configuration must be reviewed before deployment.
- Admin MFA is not implemented.
- Database schema creation uses SQLAlchemy `create_all` only in development; migrations are not implemented.
- Private media storage/endpoints do not exist. Media privacy is not implemented; the corresponding test is explicitly skipped.
- Admin features are limited to creating/disabling friends and creating letter capsules.
- Birthday unlock is 00:00 local time; February 29 birthdays unlock February 28 in non-leap years.
- Letters are JSON data; the future frontend must render their content as text, not trusted HTML.
- The frontend, browser flows, recovery process, notifications, and production deployment have not been implemented or validated.
- This branch's complete test suite must pass in GitHub Actions before its changes are considered verified. Passing CI is not a production security audit.
