# Opportunity Lifecycle

Use these working stages for active opportunity management:

- `discovery`
- `qualified`
- `proposal`
- `negotiation`
- `paused`
- `closed-won`
- `closed-lost`

Rules:
- `stage` is the canonical lifecycle field.
- `is-active` is the binary operational flag.
- `paused` means the opportunity remains open but active execution is intentionally deferred.
- Pair `paused` with an open `Task` using `status: waiting` and a future `due-date` so the review is reminder-driven.
- `closed-won` and `closed-lost` should set `is-active=false`.
- `mark-lost` should preserve `lost-at-stage`, `lost-reason`, and `lost-date`.
- stale archive is operational, not a delete path.
- Do not use `closed-lost` for "not now" unless the opportunity is actually no longer viable.
