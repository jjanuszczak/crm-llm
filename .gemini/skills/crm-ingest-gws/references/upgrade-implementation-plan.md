# Revision Spec: Align `crm-ingest-gws` with Current CRM Workflow

## Purpose

This spec updates `crm-ingest-gws` so it works with:
- the current lead lifecycle in [`crm-lead-manager`](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/SKILL.md)
- the current vault layout, including nested `Tasks`, `Activities`, and `Notes`
- the newer distinction between `Lead`, `Contact`, `Organization`, `Account`, and `Opportunity`
- a review model where one source event can produce multiple linked CRM suggestions

The current skill is directionally useful but insufficient as a core workflow without these upgrades.

## Target Behavior

### 1. Context-first entity inference

The ingester should not treat all unknown professional participants the same.

Required behavior:
- infer likely role from thread and meeting context first
- fall back to `new_lead_candidate` when uncertain
- support these staged outcomes:
  - `new_lead_candidate`
  - `new_contact_candidate`
  - `new_contact_for_existing_relationship`
  - `new_contact_for_existing_lead_context`
  - `new_contact_and_new_lead`
  - `noise`

Default rules:
- unknown professional participant with ambiguous context -> `new_lead_candidate`
- new participant in an existing lead thread -> `new_contact_for_existing_lead_context`
- new participant clearly added to an active account/opportunity thread -> `new_contact_for_existing_relationship`
- dual-role participant -> `new_contact_and_new_lead`

### 2. Lead lifecycle suggestions, not silent stage changes

The ingester should understand lead stages but not auto-change them.

Required behavior:
- stage lead lifecycle proposals instead of auto-applying them
- support:
  - `suggest_lead_status_change`
  - `suggest_lead_conversion`
- include:
  - `current_status`
  - `suggested_status`
  - `reason`
  - `evidence`
  - `conversion_mode` when relevant

Rules:
- real interaction with an existing lead can suggest `new -> engaged`
- commercial or relationship-structuring signals can suggest `engaged -> qualified`
- qualified leads with clear downstream shape can suggest conversion

### 3. Opportunity suggestions from explicit workstream formation

The ingester should not stop at generic `commercial_intent`.

Required behavior:
- stage `suggest_new_opportunity` when context clearly forms an opportunity but auto-creation is not being performed
- include:
  - proposed opportunity name
  - related lead/contact/account
  - rationale
  - evidence from email, calendar, and notes
  - suggested priority/stage when inferable

### 4. Tier policy refinement

Keep the three-tier model, but narrow automation.

Tier policy:
- Tier 1:
  - auto-create `Activity` for high-confidence matched relationships
  - dedupe must be strict
- Tier 2:
  - auto-create `Contact` only when clearly anchored to an existing active `Account` or `Opportunity`
  - never auto-create if the participant may be a separate lead center
- Tier 3:
  - lead creation
  - lead-stage proposals
  - opportunity suggestions
  - new task suggestions
  - conversion suggestions

### 5. Automatic meeting-notes enrichment

The ingester should not rely only on email snippets or calendar descriptions when meeting notes exist.

Required behavior:
- automatically look for meeting notes when the event is meeting-related and commercially relevant
- inspect:
  - explicit `meeting-notes` links in linked CRM records
  - Google Docs links in email/calendar text
  - Granola-style note links in event or message text
- use notes to improve:
  - activity summary quality
  - task extraction
  - lead-stage suggestions
  - opportunity suggestions

### 6. Task extraction discipline

Task extraction should be owner-aware.

Required behavior:
- only propose tasks when the action is clearly assigned to John or clearly belongs in John's CRM workflow
- if ownership is ambiguous, do not emit a normal task proposal
- instead emit a weaker signal such as:
  - `possible_action_item`
  - `owner_unclear`
  - `needs_meeting_notes_review`

### 7. Better activity parent resolution

The activity parent should be chosen by contextual relevance, not simply by existence of any active opportunity.

Required behavior:
- if multiple active opportunities exist, infer the most relevant one using:
  - participants
  - linked organization/account
  - commercial keywords
  - thread history
  - prior linked activities in the same thread
- if no opportunity is clearly dominant, fall back to `Contact`

### 8. Calendar relevance filtering

Unknown meeting attendees should not all become discoveries.

Required behavior:
- create discovery or relationship suggestions only for commercially or relationship-relevant calendar events
- otherwise:
  - log the activity if it belongs to an existing relationship
  - ignore unknown external participants

Signals of relevance:
- external professional domains
- business-oriented title or description
- linked CRM entities
- relationship or commercial keywords

### 9. Stronger dedupe for activity auto-write

Tier 1 auto-activity creation must be safe.

Required behavior:
- before writing an activity, scan `Activities/` recursively
- treat an activity as duplicate if:
  - `source_type` matches
  - `source_id` or `source-ref` matches
  - normalized primary parent matches

## Staging Output Refactor

Replace the current generic queues with role-specific queues.

Required files:
- `staging/activity_updates.json`
- `staging/contact_discoveries.json`
- `staging/lead_decisions.json`
- `staging/opportunity_suggestions.json`
- `staging/task_suggestions.json`
- `staging/ingestion_audit.json`
- `staging/interactions.json`
- `staging/workspace_sync_state.json`

Optional:
- `staging/noise_review.json` if needed; otherwise noise stays in audit only

## Review Order

Review the staged outputs in this fixed order:

1. `activity_updates.json`
2. `contact_discoveries.json`
3. `lead_decisions.json`
4. `opportunity_suggestions.json`
5. `task_suggestions.json`

Rationale:
- first confirm what happened
- then confirm who the people are
- then decide relationship state
- then decide whether a commercial object should exist
- then decide follow-up work

## Queue Semantics

### `activity_updates.json`

This queue should include both auto-written and review-required activity records.

Required fields:
- `status`
  - `auto_written`
  - `pending_review`
- `write_policy_tier`
- `dedupe_result`
- `target_record_path` when written
- `reason`

Ordering:
1. `pending_review`
2. `auto_written`
3. newest-first within each group

### `contact_discoveries.json`

This queue should use explicit action intent.

Required `action_type` values:
- `create_contact`
- `attach_contact_to_existing_relationship`
- `create_contact_and_flag_secondary_lead`

Required fields:
- proposed contact name
- email
- inferred company context
- linked lead/account/opportunity if applicable
- rationale
- ambiguity flags

Ordering:
1. grouped by relationship anchor
2. newest-first within each anchor group

Anchor priority:
1. existing `Opportunity`
2. existing `Lead`
3. existing `Account` or company context
4. unanchored discovery

### `lead_decisions.json`

Keep all lead-related decisions in one queue with structured decision types.

Required `decision_type` values:
- `create_lead`
- `suggest_status_change`
- `suggest_conversion`

For `suggest_conversion`, always include:
- `conversion_mode`
  - `commercial`
  - `relationship-only`
  - `undetermined`

If `conversion_mode` is `undetermined`, include the missing evidence or ambiguity explanation.

Ordering:
1. existing lead decisions grouped by `Lead`
2. net-new lead candidates grouped by `proposal_group_id`
3. newest-first within each group

### `opportunity_suggestions.json`

Default to one best candidate opportunity per source event.

Allow multiple only when the event clearly contains separate workstreams.

Required fields:
- `proposal_rank`
- `is_primary_suggestion`
- `workstream_evidence`
- proposed opportunity name
- linked lead/contact/account context
- rationale

Ordering:
1. grouped by parent context
2. `is_primary_suggestion = true` first within each group
3. then `proposal_rank`
4. then newest-first

### `task_suggestions.json`

Support both new work and completion review.

Required `task_type` values:
- `committed_action`
- `suggested_follow_up`
- `task_completion_suggestion`

Rules:
- when one event suggests both task completion and a new task, show completion first
- `committed_action` requires clear owner assignment to John
- `suggested_follow_up` covers exploratory or contingent next steps
- `task_completion_suggestion` should include:
  - matched task
  - completion evidence
  - confidence
  - suggested new status

Ordering:
1. grouped by relationship context
2. within each group:
   - `task_completion_suggestion`
   - `committed_action`
   - `suggested_follow_up`
3. newest-first within each subtype

### `noise_review.json`

Use only for borderline filtered items.

Rules:
- obvious noise stays only in `ingestion_audit.json`
- borderline cases can be surfaced in `noise_review.json`

## Proposal Grouping

One source event can produce multiple related suggestions.

Required behavior:
- every staged suggestion should include:
  - `proposal_group_id`
  - `source_event_id`
  - `source_type`
  - `source_link`
- this allows one event to produce linked actions such as:
  - contact creation for an existing relationship
  - separate lead candidate
  - lead-stage suggestion

## Evidence Layers

When notes are used for inference, preserve the reasoning chain.

Required fields where applicable:
- `source_event_summary`
- `meeting_notes_summary`
- `derived_recommendation`

This should apply to:
- lead decisions
- opportunity suggestions
- task suggestions

## Indexing and Resolver Upgrades

The resolver must be hardened for the current vault.

Required behavior:
- recurse through vault directories using `iter_markdown_files`
- index `Organizations`, `Accounts`, `Contacts`, `Leads`, `Opportunities`, and open `Tasks`
- normalize mixed link forms:
  - `[[Organizations/...]]`
  - `[[Accounts/...]]`
- use a unified `company_context` layer for matching first
- support canonical matching by:
  - email
  - domain
  - wikilink variants
  - canonicalized slug

Resolver behavior:
- match against company context first, then decide whether a proposal targets `Organization`, `Account`, or both
- detect dual-role situations when a known contact appears under a different company context
- use prior CRM activities and thread history where available to improve inference

Current issues to eliminate:
- `os.listdir()` assumptions for flat directories
- domain matching based only on `url`
- brittle literal matching of `account` and `opportunity` links

## Implementation Phases

### Phase 1. Skill and schema alignment
- update `SKILL.md`
- update `references/ingestion-logic.md`
- keep this revision spec as the implementation target

### Phase 2. Resolver and indexing hardening
- refactor indexing to recurse through nested directories
- normalize `Organizations` and `Accounts` linkage
- improve opportunity selection and task matching

### Phase 3. Staging model redesign
- split generic outputs into focused queues
- add grouped proposal IDs and structured proposal types

### Phase 4. Notes-aware inference
- add note-link detection and retrieval
- feed notes into task, lead, and opportunity inference

### Phase 5. Safe mutation layer
- preserve Tier 1 auto-activity creation
- enforce strong dedupe before write
- keep lead, opportunity, and most task decisions staged

## Acceptance Criteria

The upgrade is sufficient when:
- Mark-style cases can stage both `contact` and `lead` outcomes from one event
- new participants in existing lead threads default to contact expansion, not new standalone leads
- lead-stage suggestions appear explicitly in review queues
- opportunity suggestions are first-class outputs
- example-company/Example Company-style tasks and activities resolve to the right parent relationships
- Tier 1 activity auto-write produces no duplicates across repeated runs
- the ingester operates correctly against nested time-bucketed directories
