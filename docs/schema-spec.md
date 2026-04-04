# CRM Schema Spec v4.1

**Status:** Current

This document is the canonical current-state schema reference for the vault and logic layer.

Some current templates still include calculated or compatibility fields for operational continuity. In this document, the field status is normative: `Calculated` and `Deprecated` fields should be treated as non-canonical even if they still appear in templates today.

## Field Status

- `Canonical`: part of the intended durable schema and should be used for new writes.
- `Calculated`: derived by automation. If persisted, treat as a cache or telemetry output rather than source-of-truth.
- `Compatibility`: still written or tolerated to preserve older workflows.
- `Deprecated`: should not be used for new writes and should be removed once migration risk is low.

## Global Rules

- Dates use `YYYY-MM-DD`.
- Wikilinks in frontmatter should be quoted.
- Flat frontmatter is canonical. Do not introduce nested YAML objects.
- `source` and `source-ref` are provenance fields and should be preserved when known.
- `owner` is canonical even in the single-operator model.

## Entity Paths

- `Organizations/`
- `Accounts/`
- `Contacts/`
- `Leads/`
- `Opportunities/`
- `Activities/`
- `Notes/`
- `Tasks/`
- `Inbox/`
- `Deal-Flow/`

Note: the conceptual entity is `Deal`. The repo is still in a path transition between `Deal-Flow/` and a future `Deals/` canonical directory.

## Organizations

Stable entity identity and classification.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | `org-...` stable machine id |
| `organization-name` | Canonical | Display name |
| `domain` | Canonical | Domain or empty string |
| `headquarters` | Canonical | Freeform location |
| `industry` | Canonical | Primary sector |
| `size` | Canonical | Numeric scale signal |
| `url` | Canonical | Website |
| `organization-class` | Canonical | `investor`, `operating-company`, `financial-institution`, `government`, `service-provider`, `other` |
| `organization-subtype` | Canonical | Freeform subtype |
| `investment-mandate` | Canonical | Especially relevant for investors |
| `check-size` | Canonical | Investor profile field |
| `last-contacted` | Canonical | Persisted observed signal |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `warmth-score` | Calculated | Telemetry cache if present |
| `warmth-status` | Calculated | Telemetry cache if present |
| `velocity-score` | Calculated | Telemetry cache if present |
| `account-warmth-index` | Calculated | Legacy/telemetry aggregate if present |

## Accounts

Commercial relationship wrapper around an organization.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | `acct-...` stable machine id |
| `organization` | Canonical | `[[Organizations/...]]` |
| `owner` | Canonical | Relationship owner |
| `relationship-stage` | Canonical | `prospect`, `engaged`, `customer`, `churned` |
| `strategic-importance` | Canonical | Stable importance, not execution priority |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `source-lead` | Canonical | Optional lead provenance |
| `last-contacted` | Canonical | Persisted observed signal |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `warmth-score` | Calculated | Telemetry cache |
| `warmth-status` | Calculated | Telemetry cache |
| `velocity-score` | Calculated | Telemetry cache |
| `account-warmth-index` | Calculated | Aggregate cache |
| `stage` | Compatibility | Mirror of `relationship-stage` for old readers |
| `priority` | Deprecated | Replaced by `strategic-importance` |
| `company-name` | Deprecated | Stable identity moved to Organization |
| `type` | Deprecated | Stable classification moved to Organization |
| `headquarters` | Deprecated | Stable identity moved to Organization |
| `industry` | Deprecated | Stable identity moved to Organization |
| `size` | Deprecated | Stable identity moved to Organization |
| `url` | Deprecated | Stable identity moved to Organization |
| `investment-mandate` | Deprecated | Investor profile moved to Organization |
| `check-size` | Deprecated | Investor profile moved to Organization |
| `funding-stage` | Deprecated | Belongs on Deal, not Account |
| `target-raise` | Deprecated | Belongs on Deal, not Account |
| `days-since-contact` | Deprecated | Computed, should not be persisted |
| `migration-target` | Deprecated | Temporary migration control field |
| `migration-note` | Deprecated | Temporary migration control field |
| `hq` | Deprecated | Legacy alias |
| `website` | Deprecated | Legacy alias |
| `name` | Deprecated | Legacy alias |
| `status` | Deprecated | Ambiguous legacy field |
| `tags` | Deprecated | Unstructured legacy field |

## Contacts

Durable person records.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `full-name` | Canonical | Canonical person name |
| `nickname` | Canonical | Short display name |
| `owner` | Canonical | Record owner |
| `account` | Canonical | `[[Accounts/...]]` when tied to a commercial relationship |
| `deal` | Canonical | Optional `[[Deal-Flow/...]]` or future `[[Deals/...]]` |
| `linkedin` | Canonical | Optional |
| `email` | Canonical | Optional |
| `mobile` | Canonical | Optional |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `relationship-status` | Canonical | `active`, `dormant`, `archived` |
| `priority` | Canonical | Contact-level importance currently remains canonical |
| `last-contacted` | Canonical | Persisted observed signal |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `warmth-score` | Calculated | Telemetry cache |
| `warmth-status` | Calculated | Telemetry cache |
| `velocity-score` | Calculated | Telemetry cache |
| `days-since-contact` | Deprecated | Computed, should not be persisted |
| `full--name` | Deprecated | Legacy typo alias of `full-name` |
| `phone` | Deprecated | Legacy alias of `mobile` |
| `name` | Deprecated | Legacy alias |
| `status` | Deprecated | Ambiguous legacy field |
| `title` | Deprecated | Legacy freeform field |
| `type` | Deprecated | Legacy field |
| `tags` | Deprecated | Unstructured legacy field |

## Leads

Pre-conversion relationship candidates.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `lead-name` | Canonical | Display name |
| `status` | Canonical | `new`, `prospect`, `engaged`, `qualified`, `converted`, `disqualified` |
| `owner` | Canonical | Record owner |
| `lead-source` | Canonical | Primary source |
| `person-name` | Canonical | Optional early-stage |
| `company-name` | Canonical | Optional early-stage |
| `email` | Canonical | Optional |
| `linkedin` | Canonical | Optional |
| `priority` | Canonical | Lead importance |
| `source-ref` | Canonical | Provenance pointer |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `converted-organization` | Canonical | Set on conversion when present |
| `converted-contact` | Canonical | Set on conversion when present |
| `converted-account` | Canonical | Set on conversion when present |
| `converted-opportunities` | Canonical | Set on conversion when present |

## Opportunities

Concrete commercial or strategic engagements.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `opportunity-name` | Canonical | Display name |
| `owner` | Canonical | Record owner |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `account` | Canonical | `[[Accounts/...]]` |
| `deal` | Canonical | Optional `[[Deal-Flow/...]]` or future `[[Deals/...]]` |
| `primary-contact` | Canonical | `[[Contacts/...]]` |
| `source-lead` | Canonical | Optional `[[Leads/...]]` |
| `organization` | Canonical | `[[Organizations/...]]` |
| `opportunity-type` | Canonical | `advisory`, `consulting`, `financing`, `hiring`, `partnership`, `other` |
| `is-active` | Canonical | Boolean |
| `stage` | Canonical | Current canonical stage field |
| `commercial-value` | Canonical | Canonical value field |
| `close-date` | Canonical | Target or realized close date |
| `probability` | Canonical | Integer percentage |
| `product-service` | Canonical | Offer, mandate, or engagement label |
| `influencers` | Canonical | Contact links |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `lost-at-stage` | Canonical | Populated for closed-lost paths |
| `lost-reason` | Canonical | Populated for closed-lost paths |
| `lost-date` | Canonical | Populated for closed-lost paths |
| `deal-value` | Compatibility | Mirror of `commercial-value`; remove after reader cleanup |
| `type` | Deprecated | Legacy ad hoc schema |
| `name` | Deprecated | Legacy ad hoc schema |
| `status` | Deprecated | Legacy ad hoc schema |
| `value` | Deprecated | Legacy ad hoc schema |
| `tags` | Deprecated | Legacy ad hoc schema |

## Activities

Event records and interaction history.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `activity-name` | Canonical | Display name |
| `activity-type` | Canonical | `call`, `email`, `meeting`, `analysis`, `note-derived` |
| `status` | Canonical | `completed`, `scheduled`, `cancelled` currently tolerated |
| `owner` | Canonical | Record owner |
| `date` | Canonical | Activity date |
| `primary-parent-type` | Canonical | `opportunity`, `contact`, `account`, `lead`, `deal` |
| `primary-parent` | Canonical | Primary wikilink |
| `secondary-links` | Canonical | Secondary wikilinks |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `email-link` | Canonical | Optional deep link |
| `meeting-notes` | Canonical | Optional note pointer |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `activity-date` | Compatibility | Legacy alias of `date` |
| `account` | Deprecated | Legacy redundant link |
| `contact` | Deprecated | Legacy redundant link |
| `contacts` | Deprecated | Legacy redundant link |
| `opportunity` | Deprecated | Legacy redundant link |
| `channel` | Deprecated | Legacy freeform field |
| `subject` | Deprecated | Legacy freeform field |
| `tasks` | Deprecated | Legacy freeform field |
| `tags` | Deprecated | Legacy freeform field |
| `type` | Deprecated | Legacy alias |

## Notes

Durable context and strategic memory.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `title` | Canonical | Display name |
| `owner` | Canonical | Record owner |
| `primary-parent-type` | Canonical | `lead`, `contact`, `account`, `opportunity`, `deal`, `activity` |
| `primary-parent` | Canonical | Primary wikilink |
| `secondary-links` | Canonical | Secondary wikilinks |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `note-name` | Deprecated | Legacy alias |
| `date` | Deprecated | Legacy extra date field |

## Tasks

Explicit next actions.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `task-name` | Canonical | Display name |
| `status` | Canonical | `todo`, `in-progress`, `blocked`, `done`, `canceled` |
| `priority` | Canonical | Execution priority |
| `owner` | Canonical | Record owner |
| `due-date` | Canonical | Due date |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |
| `primary-parent-type` | Canonical | `lead`, `contact`, `account`, `opportunity`, `deal` |
| `primary-parent` | Canonical | Primary wikilink |
| `account` | Canonical | Convenience link |
| `contact` | Canonical | Convenience link |
| `opportunity` | Canonical | Convenience link |
| `lead` | Canonical | Convenience link |
| `type` | Canonical | Currently `follow-up` in templates |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `email-link` | Canonical | Optional deep link |
| `meeting-notes` | Canonical | Optional note pointer |
| `parent` | Deprecated | Legacy alias |
| `deal` | Deprecated | Legacy extra link |
| `date` | Deprecated | Legacy extra date field |
| `tags` | Deprecated | Legacy freeform field |

## Inbox Items

Temporary raw capture.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `title` | Canonical | Display title |
| `status` | Canonical | `new`, `processing`, `processed`, `ignored` |
| `owner` | Canonical | Record owner |
| `source` | Canonical | `manual`, `gmail`, `calendar`, `voice`, `inbox-forward` |
| `source-ref` | Canonical | Provenance pointer |
| `captured-at` | Canonical | Capture date |
| `date-created` | Canonical | Creation date |
| `date-modified` | Canonical | Last mutation date |

## Deals

Fundraising inventory object. Current vault path is `Deal-Flow/`.

| Field | Status | Notes |
| :--- | :--- | :--- |
| `id` | Canonical | Stable machine id |
| `startup-name` | Canonical | Display name |
| `owner` | Canonical | Record owner |
| `sector` | Canonical | Primary sector |
| `fundraising-stage` | Canonical | Startup financing stage |
| `coverage-status` | Canonical | Internal workflow status |
| `location` | Canonical | Geography |
| `traction-metrics` | Canonical | Compact traction summary |
| `target-raise` | Canonical | Raise target |
| `currency` | Canonical | Currency code |
| `valuation-cap` | Canonical | Numeric valuation field |
| `pitch-deck-url` | Canonical | Optional |
| `google-drive-url` | Canonical | Optional |
| `founder-contacts` | Canonical | Contact links |
| `related-accounts` | Canonical | Account links |
| `related-opportunities` | Canonical | Opportunity links |
| `source` | Canonical | Provenance |
| `source-ref` | Canonical | Provenance pointer |
| `date-sourced` | Canonical | Sourcing date |
| `date-modified` | Canonical | Last mutation date |
| `stage` | Deprecated | Legacy alias of fundraising stage |
| `datesourced` | Deprecated | Legacy typo alias |
| `last-contacted` | Calculated | Telemetry cache if present |
| `warmth-score` | Calculated | Telemetry cache if present |
| `warmth-status` | Calculated | Telemetry cache if present |
| `velocity-score` | Calculated | Telemetry cache if present |
| `account-warmth-index` | Calculated | Telemetry cache if present |
| `days-since-contact` | Deprecated | Computed, should not be persisted |

## Calculated Signals Summary

These are currently used by the dashboard and intelligence layers, but they are not core business truth:

- `warmth-score`
- `warmth-status`
- `velocity-score`
- `account-warmth-index`
- `days-since-contact`

`last-contacted` is different: it is an observed persisted signal and remains canonical.

## Highest Priority Future Cleanup

1. Remove `deal-value` once all readers rely only on `commercial-value`.
2. Stop writing calculated fields into templates where they are not needed as caches.
3. Remove legacy aliases such as `full--name`, `activity-date`, `stage` on Accounts, and old ad hoc Opportunity fields.
4. Complete `Deal-Flow/` to `Deals/` path normalization.
