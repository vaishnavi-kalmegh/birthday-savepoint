# Implementation Plan

This plan is provisional until the existing repository has been inspected. Do not assume the repository is empty or scaffold over existing work.

## Stage 0: Repository audit

- Inspect Git status and tracked files.
- Read the existing README, manifests, backend entrypoint, configuration, tests, and migrations.
- Summarize what already exists and identify the smallest safe next step.
- Do not edit application files until the audit is complete.

## Stage 1: Minimal foundation

- Agree on repository structure based on what exists.
- Add only necessary project configuration and developer documentation.
- Establish environment-variable handling and safe example configuration.
- Add CI checks only when the corresponding project commands exist.
- Avoid introducing database/object-storage infrastructure before the first slice needs it.

## Stage 2: Authentication and authorization foundation

- Implement secure login/logout and revocable sessions.
- Add server-side authorization helpers and rate limits.
- Write tests for unauthenticated access and cross-account isolation before building private capsule features.

## Stage 3: One visual environment

- Build design tokens and one original, polished pixel-art environment.
- Make theme configuration data-driven without overengineering a universal scene engine prematurely.
- Check responsive behavior, keyboard accessibility, reduced motion, and real interaction behavior.

## Stage 4: Birthday capsule and server-enforced lock

- Add a birthday letter capsule.
- Implement server-side unlock calculation and safe locked responses.
- Test that future content and media references are never exposed before unlock.
- Explicitly decide and test timezone and February 29 policies.

## Stage 5: Admin and media

- Add admin-only friend/capsule management.
- Add private media access with server authorization.
- Test cross-account and direct-media access paths.

## Stage 6: Notifications

- Add a manual reminder path first.
- Add durable delivery status, retries, and idempotency.
- Integrate an email provider only after checking current requirements, cost, limits, and payment-method requirements.

## Stage 7: Expansion and release hardening

- Add more themes and capsule formats.
- Run backend, frontend, security, and end-to-end tests.
- Document local setup and deployment assumptions.
- Report any unverified behavior honestly.
