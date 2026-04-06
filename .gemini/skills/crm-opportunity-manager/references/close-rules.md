# Close Rules

Won:
- set `stage=closed-won`
- set `probability=100`
- set `is-active=false`
- confirm `close-date`
- keep the opportunity as durable history

Lost:
- set `stage=closed-lost`
- set `probability=0`
- set `is-active=false`
- populate `lost-at-stage`
- populate `lost-reason`
- populate `lost-date`

Stale:
- use when the opportunity should remain historical but is no longer operationally active
- set `is-active=false`
- preserve all history
- optionally create a recheck task if the operator wants a later revisit
