# Opportunity Lifecycle

Use these working stages for active opportunity management:

- `discovery`
- `qualified`
- `proposal`
- `negotiation`
- `closed-won`
- `closed-lost`

Rules:
- `stage` is the canonical lifecycle field.
- `is-active` is the binary operational flag.
- `closed-won` and `closed-lost` should set `is-active=false`.
- `mark-lost` should preserve `lost-at-stage`, `lost-reason`, and `lost-date`.
- stale archive is operational, not a delete path.
