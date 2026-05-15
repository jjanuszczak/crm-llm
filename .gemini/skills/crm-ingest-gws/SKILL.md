---
name: crm-ingest-gws
description: Ingest Gmail and Calendar activity into staged CRM decisions, relationship updates, and safe activity writes using context-aware matching and review queues.
---

# CRM Ingest GWS

## Overview

This skill ingests Gmail and Calendar activity into the CRM as a staged decision workflow.

Its job is not just to sync events. It should:
- log trusted activity for known relationships
- expand known relationships with new contacts when context is clear
- infer lead, opportunity, and task suggestions from communication context
- use prior CRM history and meeting notes when available
- separate factual activity logging from judgment-heavy relationship decisions

This skill must stay aligned with the lead lifecycle defined in [`crm-lead-manager`](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/SKILL.md).

## Current Status

The current script exists and is usable:

```bash
python3 .gemini/skills/crm-ingest-gws/scripts/ingest.py [--since YYYY-MM-DD] [--auto-tier N] [--skip-granola]
```

Codex desktop execution note: this script calls `gws`, which must reach Gmail, Calendar, Docs, and Drive APIs. In the restricted Codex sandbox this commonly fails with DNS / host-resolution errors before ingest starts. For the recurring CRM daily automation, run it through the approved unrestricted command path:

```bash
/bin/zsh -lc 'set -a; [ -f .env ] && . ./.env; set +a; CRM_DATA_PATH=${CRM_DATA_PATH:-./crm-data} python3 .gemini/skills/crm-ingest-gws/scripts/ingest.py --autonomous --auto-tier 1'
```

If a sandboxed attempt fails with a Google API network error, rerun the same command with escalation immediately. Do not report the daily automation as blocked until that unrestricted rerun has also failed.

But the current implementation is not yet fully aligned with:
- the newer lead lifecycle
- the split review queues
- stronger dedupe requirements
- notes-aware inference
- hardened resolver/indexing for the current vault

Use this skill with those gaps in mind until the script is upgraded.

The active revision target is:
- [references/upgrade-implementation-plan.md](references/upgrade-implementation-plan.md)
- Visual logic map: [references/flowchart.md](references/flowchart.md)

## When To Use

Use this skill when you need to:
- ingest new Gmail or Calendar activity into the CRM
- stage new contacts, leads, opportunities, or task suggestions from communication data
- review unknown participants and decide whether they are contacts, leads, or noise
- propose lead stage changes from interaction evidence
- mine relationship-relevant meeting notes for richer CRM updates
- optionally enrich the review with Granola meeting notes when Granola MCP is available

## Operating Model

### 1. Ingest and normalize source events

Run the ingester to scan deltas from Gmail and Calendar.

```bash
python3 .gemini/skills/crm-ingest-gws/scripts/ingest.py [--since YYYY-MM-DD] [--auto-tier N]
```

Core pipeline:
- **Harvester**: pulls Gmail and Calendar deltas through `gws`
- **Normalizer**: converts source payloads into a canonical event shape
- **Resolver**: matches events against CRM entities and company context
- **Inferrer**: derives relationship, lead, opportunity, and task signals
- **Stager**: writes review queues and audit outputs

Current extension:
- an end-of-run Drive pass may also review CRM-labeled Google Docs after the main Gmail / Calendar flow
- an end-of-run Granola pass may also review recent Granola meetings and write deduped Activities / Tasks when Granola MCP is available through local Codex

### 2. Use contextual inference, not flat discovery

Unknown professional participants should not all be treated the same.

The target behavior is:
- infer whether the participant is:
  - a new lead candidate
  - a new contact candidate
  - a contact for an existing relationship
  - both a contact and a secondary lead
  - noise
- if uncertain, fail safe to `new_lead_candidate`
- if the participant is in an existing lead thread, default to contact expansion unless they clearly represent a separate relationship center
- if the participant is clearly anchored to an active account or opportunity and is just an added stakeholder, contact creation may be automated at Tier 2

### 3. Keep activity writes separate from relationship decisions

This skill uses a three-tier model:

| Tier | Policy | Allowed behavior |
| :--- | :--- | :--- |
| `1` | Safe auto-write | Auto-create non-duplicate `Activity` records for high-confidence matched relationships |
| `2` | Auto with audit | Auto-create `Contact` only when clearly anchored to an active relationship and non-ambiguous |
| `3` | Review required | Lead decisions, opportunity suggestions, task suggestions, ambiguous contact discovery, conversion suggestions |

Rules:
- Tier 1 activity writing stays enabled
- auto-written Activity bodies must summarize the source event into CRM memory; do not paste or truncate the raw email/calendar text as the executive summary
- preserve source provenance through `source`, `source-ref`, `email-link`, `meeting-notes`, and at most a short source excerpt for auditability
- no automatic lead stage change
- no automatic task completion
- no automatic opportunity creation from inferred context unless explicitly added later

### 4. Respect the lead lifecycle

This skill should reason using the lead stages from `crm-lead-manager`:
- `new`
- `engaged`
- `qualified`
- `converted`

But it should not mutate those stages automatically.

Instead, it should stage:
- `create_lead`
- `suggest_status_change`
- `suggest_conversion`

And for conversion suggestions it should always include:
- `conversion_mode = commercial`
- `conversion_mode = relationship-only`
- or `conversion_mode = undetermined`

### 5. Always look for meeting notes in Google Drive first

When the ingester processes a calendar entry or relationship-relevant email, it should always run a meeting-notes lookup step before finalizing activity, task, lead, or opportunity suggestions.

The lookup order should include:
- Google Docs links already present in the email or calendar text
- Granola note links already present in the email or calendar text
- existing `meeting-notes` fields on linked CRM records
- a best-effort Google Drive search for likely meeting notes even when the source event does not already contain a note link

Meeting notes should enrich:
- activity summaries
- task suggestions
- lead decisions
- opportunity suggestions

When notes are used, preserve:
- `source_event_summary`
- `meeting_notes_summary`
- `derived_recommendation`

If the Drive search finds a likely Google Doc, the ingester should read the document text and use it as additional context for:
- signal detection
- action-item extraction
- activity write quality
- review queue summaries

The current implementation may also run a labeled-document Drive pass after the main event processing. That pass is additive, not a replacement for the earlier broad lookup behavior.

### 5a. Optionally enrich with Granola after the main ingest

If Granola MCP is connected in local Codex, the ingester may run a post-ingest Granola pass automatically after the normal Gmail / Calendar / Drive ingest has completed. Use `--skip-granola` to disable that pass for a given run.

Use Granola to:
- search for recent meeting notes that were not picked up through the standard event-driven path
- pull action items, decisions, or summaries from recent meetings
- validate or enrich `task_suggestions.json`, `activity_updates.json`, and note creation decisions

Rules:
- Granola is optional and interactive; do not make this skill depend on it for baseline success
- the main Gmail / Calendar / Drive logic remains the first-pass source of truth
- if Granola finds useful additional context, convert that into durable CRM updates with explicit provenance and dedupe by Granola `source-ref`
- if Granola is unavailable, disconnected, or returns no relevant meetings, continue without blocking

### 6. Treat tasks conservatively

Task logic should be careful:
- only propose new tasks when the action is clearly assigned to John or clearly belongs in John's CRM workflow
- allow both:
  - `committed_action`
  - `suggested_follow_up`
- do not auto-complete tasks
- stage `task_completion_suggestion` when later evidence indicates a task may now be complete

When both completion and new work are suggested from the same event, completion should be reviewed first.

## Review Queues

The target queue structure is:
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
- `staging/drive_document_updates.json` for the post-ingest CRM-labeled Google Docs pass
- `staging/granola_updates.json` for the post-ingest Granola pass

Review in this order:
1. `activity_updates.json`
2. `contact_discoveries.json`
3. `lead_decisions.json`
4. `opportunity_suggestions.json`
5. `task_suggestions.json`
6. `drive_document_updates.json` when present
7. `granola_updates.json` when present

Why:
- first confirm what happened
- then who the participants are
- then what relationship state applies
- then whether an opportunity should exist
- then what follow-up work should be tracked
- then inspect any additional labeled-document imports or skips
- then inspect any Granola-created or Granola-skipped records

## Queue Semantics

### `activity_updates.json`
- includes both `pending_review` and `auto_written`
- group `pending_review` first, then `auto_written`
- sort newest-first within each group

### `contact_discoveries.json`
- use explicit action types:
  - `create_contact`
  - `attach_contact_to_existing_relationship`
  - `create_contact_and_flag_secondary_lead`
- group by relationship anchor:
  - opportunity
  - lead
  - account or company context
  - unanchored discovery

### `lead_decisions.json`
- use:
  - `create_lead`
  - `suggest_status_change`
  - `suggest_conversion`
- group existing leads by lead record
- group net-new items by `proposal_group_id`

### `opportunity_suggestions.json`
- default to one best suggestion per event
- allow multiple only for clearly separate workstreams
- group by parent context
- primary suggestion first within each group

### `task_suggestions.json`
- use:
  - `task_completion_suggestion`
  - `committed_action`
  - `suggested_follow_up`
- group by relationship context
- review completion before new work

## Resolver Expectations

The resolver should use a unified company-context layer for matching before deciding whether a result belongs to:
- `Organization`
- `Account`
- both

It should:
- recurse through nested vault directories
- normalize `Organizations/...` and `Accounts/...` links
- use prior CRM activities and thread history where possible
- detect dual-role situations when a known contact appears under a different company context

## Dedupe Expectations

Tier 1 activity auto-write is only acceptable if dedupe is strict.

Activity dedupe should validate:
- `source_type`
- `source_id` or `source-ref`
- normalized primary parent

The script should scan `Activities/` recursively before writing.

When Granola-derived updates are converted into CRM records manually through this skill, they should also preserve durable provenance in `source` / `source-ref` so future ingest and review logic can avoid duplicate memory.

## References

- Lifecycle and conversion context: [../crm-lead-manager/SKILL.md](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/SKILL.md)
- Ingestion logic notes: [references/ingestion-logic.md](references/ingestion-logic.md)
- Revision target: [references/upgrade-implementation-plan.md](references/upgrade-implementation-plan.md)
- Visual flow: [references/flowchart.md](references/flowchart.md)

## Implementation Note

Until the script catches up, do not describe the full target queue model as already implemented. Use the revision spec as the source of truth for the intended workflow, and treat the current script as a partial implementation moving toward that model.
