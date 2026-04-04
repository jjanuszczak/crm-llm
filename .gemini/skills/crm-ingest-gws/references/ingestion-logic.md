# CRM Ingestion Logic Reference

## Purpose

This reference defines the intended low-level logic for `crm-ingest-gws`.

It should be read together with:
- [../SKILL.md](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-ingest-gws/SKILL.md)
- [upgrade-implementation-plan.md](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-ingest-gws/references/upgrade-implementation-plan.md)
- [../../crm-lead-manager/SKILL.md](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/SKILL.md)

## Matching Model

### Company-context first

The resolver should first infer a unified `company_context`, then decide whether the target CRM object is:
- `Organization`
- `Account`
- both

Matching inputs should include:
- participant email
- email domain
- normalized organization/account names
- wikilink variants
- canonicalized slugs
- prior thread-linked CRM activity

### Entity match priority

Preferred matching order:
1. exact email match to `Opportunity`-anchored contact context
2. exact email match to `Contact`
3. exact email match to `Lead`
4. company-context match to known `Organization`/`Account`
5. thread-context match from prior CRM activity
6. no reliable match

### Dual-role detection

If a known contact appears in a different company context than their current CRM linkage, treat it as a possible dual-role case.

Expected outcomes may include:
- attach to existing relationship
- create secondary lead
- create contact and flag secondary lead

Do not assume the same relationship center automatically.

## Activity Parent Resolution

### Goal

Choose the most contextually relevant primary parent for a new `Activity`.

### Parent selection order

Use this precedence only after contextual scoring:
1. most relevant active `Opportunity`
2. `Contact`
3. `Lead`
4. `Account` or `Organization`

### Contextual signals

When multiple candidate parents exist, score relevance using:
- participants in the event
- matched account or organization context
- commercial keywords
- prior CRM activities in the same thread
- recent linked notes
- existing lead/opportunity associations for the contact

If no opportunity is clearly dominant, fall back to `Contact`.

## Lead Inference Rules

### Unknown participant handling

Do not treat every unknown professional participant as the same type of discovery.

Allowed inferred outcomes:
- `new_lead_candidate`
- `new_contact_candidate`
- `new_contact_for_existing_relationship`
- `new_contact_for_existing_lead_context`
- `new_contact_and_new_lead`
- `noise`

Fallback:
- if uncertain, default to `new_lead_candidate`

### Existing lead thread rule

If a new participant appears in a thread already centered on an existing lead:
- default to contact expansion
- only propose a separate lead when there is evidence of a distinct relationship center

### Active relationship rule

If a new participant appears in a clearly anchored active account or opportunity thread:
- they may be auto-created as a contact at Tier 2
- only if they are clearly an additional stakeholder
- never auto-create if they may be a separate lead center

## Lead Lifecycle Suggestions

The ingester should understand lead stages but never auto-change them.

Allowed lead decision outputs:
- `create_lead`
- `suggest_status_change`
- `suggest_conversion`

### Status-change rules

Examples:
- real email/call/meeting with known lead -> may suggest `new -> engaged`
- strong relationship intent with known contact and organization -> may suggest `engaged -> qualified`

### Conversion rules

If conversion is suggested, always include:
- `conversion_mode = commercial`
- `conversion_mode = relationship-only`
- or `conversion_mode = undetermined`

If `undetermined`, explain what evidence is missing.

## Opportunity Suggestion Rules

Use explicit opportunity suggestions when a workstream is clearly forming.

Required output:
- `suggest_new_opportunity`

Required fields:
- proposed opportunity name
- parent lead/contact/company context
- rationale
- workstream evidence
- suggested stage or priority when inferable

Default behavior:
- one best opportunity suggestion per event
- multiple only if the event clearly contains distinct workstreams

## Task Logic

### New task suggestion rules

Only create a task suggestion when the action is clearly assigned to John or clearly belongs in John's CRM workflow.

Allowed task suggestion types:
- `committed_action`
- `suggested_follow_up`

Do not treat ambiguous commitments as normal tasks by default.

For ambiguous cases, emit signals such as:
- `possible_action_item`
- `owner_unclear`
- `needs_meeting_notes_review`

### Task completion rules

Task completion should never be auto-applied.

Allowed output:
- `task_completion_suggestion`

Required fields:
- matched task
- evidence
- confidence
- suggested new status

If one event suggests both task completion and a new task:
- review completion first

## Meeting Notes Enrichment

### When to look for notes

For commercially or relationship-relevant meetings, automatically inspect likely note sources:
- `meeting-notes` fields on linked CRM records
- Google Docs links in event or email text
- Granola note links in event or email text

### How notes are used

Meeting notes should improve:
- activity summaries
- task extraction
- lead-stage suggestions
- opportunity suggestions

When notes are used, preserve:
- `source_event_summary`
- `meeting_notes_summary`
- `derived_recommendation`

## Calendar Relevance Filtering

Unknown attendees from calendar events should not all become discovery items.

Create discovery or relationship suggestions only when the event is commercially or relationship relevant.

Useful relevance signals:
- external professional domains
- business-oriented title or description
- known CRM entities in the invite
- commercial keywords

Otherwise:
- log the event if it belongs to an existing relationship
- ignore unknown attendees

## Dedupe Rules

### Activity dedupe

Before writing a new activity, scan `Activities/` recursively.

Treat the activity as duplicate if:
- `source_type` matches
- `source_id` or `source-ref` matches
- normalized primary parent matches

### Why this is required

Tier 1 auto-write is only safe if duplicate writes are blocked across repeated ingestion runs.

## Queue Targets

The target outputs are:
- `staging/activity_updates.json`
- `staging/contact_discoveries.json`
- `staging/lead_decisions.json`
- `staging/opportunity_suggestions.json`
- `staging/task_suggestions.json`
- `staging/ingestion_audit.json`
- `staging/interactions.json`
- `staging/workspace_sync_state.json`

Optional:
- `staging/noise_review.json` for borderline filtered items

## Review Order

Process queues in this order:
1. `activity_updates.json`
2. `contact_discoveries.json`
3. `lead_decisions.json`
4. `opportunity_suggestions.json`
5. `task_suggestions.json`

## Checkpointing

- Persistent state: `crm-data/staging/workspace_sync_state.json`
- Fields:
  - `gmail_last_sync_at`
  - `calendar_last_sync_at`
- Format: ISO 8601 in UTC
- Manual override: `--since`
