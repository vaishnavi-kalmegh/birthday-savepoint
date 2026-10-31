# Decisions

Decisions that affect security, privacy, or behavior. Each one was chosen explicitly by the project owner; change them deliberately and update the tests that pin them.

## D1. Unlock moment: local midnight on the birthday

A capsule unlocks at 00:00 on the birthday date in the friend's stored IANA timezone (`friends.timezone`).

- The unlock moment is computed on the server and stored in UTC on the capsule (`capsules.unlock_at`). It is never accepted from a client.
- If local midnight does not exist (a daylight-saving gap at 00:00), the unlock moment is the first instant of that local day. If it occurs twice, the earlier occurrence is used. In both cases the unlock moment is the earliest instant whose local date is the birthday date.
- The browser clock is never trusted. Countdowns in the UI are informational; the server decides.

## D2. February 29 birthdays in non-leap years: February 28

Each friend has a stored `leap_day_policy` (`feb28` or `mar1`). The default for new accounts is `feb28`. The policy only matters for friends born on February 29. In leap years the capsule unlocks on February 29.

## D3. Initial passwords and recovery: admin hands them over

- The admin tooling generates a random one-time password, shown once, and the owner sends it to the friend privately. It is never placed in a URL.
- A friend with a one-time password must change it before any capsule or gift endpoint responds (`must_change_password`).
- There is no self-service recovery. A forgotten password is reset by the admin, which also revokes all of that friend's sessions.
- The private entry link identifies the account but does not authenticate it. Access needs the password too.

## Still open

- Production hosting and private media storage provider.
- Notification provider (email), after current limits, card requirements, and costs are checked.
