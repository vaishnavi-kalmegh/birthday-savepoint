# Project Context: birthday-savepoint

## Product summary

A private birthday time-capsule site for a group of 10+ friends. Each friend signs in and sees a personalized environment based on their interests. They can open birthday capsules intended for them, revisit past capsules, and see a safe locked state for future capsules. Capsule content can vary by person and year: letters, playlists, video edits, scrapbooks, and similar gifts.

## Example personalization

- Yash: original comic-book-inspired rooftop/city scene.
- Aditya: cat-themed scene.
- Kartik: motorsport / racing-inspired scene.
- Diya: a distinct cat-themed scene that is not a copy of Aditya's.

These are creative directions, not permission to use copyrighted characters, logos, or assets. Prefer original or properly licensed artwork.

## Experience goals

- Atmospheric, crafted pixel-art / indie-game aesthetic.
- Smooth, purposeful motion; responsive layouts; reduced-motion support.
- No emojis in the interface, generic birthday templates, fake controls, or generic SaaS dashboard feel.
- A friend's theme should change scene composition, interaction, motion, typography, and capsule presentation, not merely colors.

## Release-one scope

One friend can securely log in, see one polished personalized scene, open a birthday letter when unlocked, and see a future capsule locked by server-side logic. Automated tests must prove that one account cannot access another account's content and that future gift content is not leaked to the client.

## Deferred scope

- Admin management for friends, birthdays, themes, capsules, uploads, and sessions.
- Notification scheduler with delivery tracking and retry/idempotency.
- More themes and gift formats.
- Production media storage and deployment provider selection.
- Optional email notifications after provider requirements and costs are verified. WhatsApp is not required for release one.

## Open decisions that must be explicit

1. Birthday unlock time and timezone policy.
2. February 29 birthday behavior in non-leap years.
3. Initial password delivery and account recovery.
4. Production hosting and private media storage provider.
5. Notification provider, if any, after verifying current free limits, card requirements, and cost.

Do not silently finalize decisions that affect security, privacy, or ongoing cost.
