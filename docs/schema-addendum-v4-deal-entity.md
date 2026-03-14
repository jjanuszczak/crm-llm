# Schema Addendum: CRM v4.0 Deal Entity Alignment

**Status:** Draft
**Depends On:**
- [prd-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/prd-v4-memory-system.md)
- [schema-addendum-v4-existing-entities.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-addendum-v4-existing-entities.md)

## 1. Purpose
This document defines recommended v4 updates for the `Deal` entity.

`Deal` remains distinct from `Account` and `Opportunity` in v4. It is still the inventory object representing a company or project seeking capital. The goal here is not to collapse that distinction, but to align `Deal` with the same provenance, ownership, and memory conventions introduced elsewhere in v4.

## 2. Current Gaps
The current Deal model is still mostly pre-v4:
- no `id`
- no `owner`
- no `source`
- no `source-ref`
- ambiguous `stage` semantics
- no explicit distinction between fundraising stage and internal coverage state
- inconsistent repo usage between `Deals/` and `Deal-Flow/`

## 3. Recommended v4 Direction

```yaml
id: "deal-example-startup"
startup-name: "Example Startup"
owner: "john"
sector: "Fintech"
fundraising-stage: "Series A"
coverage-status: "active"
location: "Singapore"
traction-metrics: "ARR $1.2M; 40% QoQ growth"
target-raise: 8000000
currency: "USD"
valuation-cap: 40000000
pitch-deck-url: "https://..."
google-drive-url: "https://..."
source: "manual"
source-ref: "drive-folder-or-email-thread"
date-sourced: 2026-03-14
date-modified: 2026-03-14
```

## 4. Recommendations

### 4.1 Shared v4 Fields
Add:
- `id`
- `owner`
- `source`
- `source-ref`

These should work the same way they now do for `Lead`, `Contact`, `Account`, `Opportunity`, and `Task`.

### 4.2 Clarify Stage Semantics
The current `stage` field appears to mean fundraising stage. That is valid, but it should be named more clearly.

Recommended:
- rename the current `stage` concept to `fundraising-stage`
- add a separate optional `coverage-status` for internal workflow if needed, for example:
  - `active`
  - `parked`
  - `closed`
  - `passed`

This prevents confusion between the startup's financing stage and the operator's relationship or coverage status.

### 4.3 Relationship Links
Deals should remain inventory, but they should support lightweight relational context.

Consider adding optional fields such as:
- `founder-contacts`
- `related-accounts`
- `related-opportunities`

These do not need to replace body content, but they would make AI retrieval and matching more reliable.

### 4.4 Matchmaker Compatibility
Any Deal schema update should be reviewed together with:
- [matchmaker.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/matchmaker.py)
- [create-deal/SKILL.md](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/create-deal/SKILL.md)
- [matchmaker/SKILL.md](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/matchmaker/SKILL.md)

In particular:
- field names used by matchmaker should stay explicit and machine-safe
- any migration from `stage` to `fundraising-stage` should preserve compatibility until the matching logic is updated

### 4.5 Directory Naming Cleanup
The repo currently mixes `Deals/` and `Deal-Flow/`.

This should be normalized. Recommended direction:
- use one canonical directory name
- update skills and scripts to match
- preserve compatibility temporarily if the private vault still contains older paths

## 5. Recommended Backlog Scope
Recommended implementation scope for Deal alignment:
1. update `templates/deal-template.md`
2. update `create-deal` instructions
3. review `matchmaker.py` and `matchmaker` skill compatibility
4. decide canonical `Deals/` vs `Deal-Flow/`
5. add backward-compatible parsing if the old field names or directory names are still present
