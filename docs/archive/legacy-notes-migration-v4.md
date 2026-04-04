# Legacy Notes Migration for v4

## Purpose
This document defines how to handle legacy `Notes/` content now that v4 treats `Inbox`, `Note`, and `Activity` as separate concepts.

## Decision Rules
Use these rules when reviewing an existing legacy note:

1. Keep it as a `Note`
If the file contains durable context such as:
- relationship background
- research
- strategic interpretation
- meeting preparation context
- reference material worth preserving

2. Migrate it into an `Activity`
If the file primarily documents a real interaction or event such as:
- an email exchange
- a meeting
- a call
- an intro made
- a follow-up sent

In these cases:
- create or preserve an `Activity`
- optionally create a supporting `Note` if the file also contains durable context beyond the event itself

3. Treat it as old raw capture and retire it
If the file is mostly temporary scratch material such as:
- rough drafts
- incomplete pasted notes
- unprocessed snippets
- raw capture that no longer needs to persist

Do not preserve the old “Notes as inbox” behavior. Future raw intake should go into `Inbox/`.

## Heuristics
Signals a file should remain a `Note`:
- analysis-heavy content
- background context with few or no timestamps
- strategic implications that remain useful after the event passes

Signals a file should become an `Activity`:
- explicit event date
- action items from a meeting or email
- subject-line style naming
- participant-specific interaction summary

Signals a file was really an old inbox artifact:
- fragmented or partial thoughts
- no stable parent relationship
- no durable insight beyond the moment of capture

## Migration Guidance
- Prefer one primary parent plus optional secondary links.
- For event-derived content, `Opportunity` should be the primary parent when present, then `Contact`, then `Account`.
- Preserve provenance where possible with `source` and `source-ref`.
- Do not mass-delete legacy notes blindly; classify them first.

## Operational Guidance
- New raw capture goes to `Inbox/`.
- New durable context goes to `Notes/`.
- New interactions go to `Activities/`.
- If a single source contains both event history and durable context, it may legitimately produce both a `Note` and an `Activity`.
