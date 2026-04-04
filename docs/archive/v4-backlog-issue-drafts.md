# CRM v4 Backlog Issue Drafts

**Target repo:** `jjanuszczak/crm-logic`
**Intended label:** `enhancement`
**Source docs:**
- [prd-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/prd-v4-memory-system.md)
- [implementation-plan-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/implementation-plan-v4-memory-system.md)
- [schema-addendum-v4-core-records.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-addendum-v4-core-records.md)

This file contains issue-ready backlog drafts for CRM v4 implementation.

## 1. Define v4 Templates and Shared Schema Helpers

**Title**
`Define v4 templates and shared schema helpers for Lead, Inbox, Note, and Activity`

**Labels**
`enhancement`

**Body**
Implement the v4 schema foundation across templates and parsing helpers so the new core record types are consistent and machine-safe.

Scope:
- add or update templates for `Lead`, `Inbox Item`, `Note`, and `Activity`
- update existing templates where link and provenance conventions need alignment
- centralize frontmatter parsing/normalization into shared helpers
- support common fields such as `id`, `owner`, `source`, `source-ref`, `date-created`, and `date-modified`
- support `primary-parent` plus `secondary-links` conventions

Acceptance criteria:
- valid v4 records can be created manually from templates
- shared parsing logic handles the new fields consistently
- existing scripts do not break when new v4 record types are present
- template and helper behavior aligns with `docs/schema-addendum-v4-core-records.md`

## 2. Introduce Lead as a First-Class Record Type

**Title**
`Introduce Lead as a first-class record type with v4 lifecycle support`

**Labels**
`enhancement`

**Body**
Add a first-class `Lead` entity to the vault model and support the v4 lifecycle.

Scope:
- create `Leads/` support and a `create-lead` workflow
- support statuses:
  - `new`
  - `prospect`
  - `engaged`
  - `qualified`
  - `converted`
  - `disqualified`
- support sparse early leads
- support `lead-source` and `owner`
- support person-only or company-only leads in early stages
- support revival from `disqualified`

Acceptance criteria:
- leads can be created and updated in valid v4 format
- status transitions follow PRD rules
- `new` leads can be sparse
- `qualified` leads enforce the minimum required fields for conversion readiness
- `disqualified` leads can be revived programmatically or manually

## 3. Implement Lead Conversion to Contact, Account, and Opportunity

**Title**
`Implement Lead conversion workflow to Contact, Account, and Opportunity`

**Labels**
`enhancement`

**Body**
Implement the default v4 lead conversion path:
`Lead -> Contact + Account + Opportunity`

Scope:
- create conversion workflow and helper logic
- validate required fields before conversion
- allow one default `Opportunity` on conversion
- support multiple `Opportunity` records only when distinct paths are clear or explicitly directed
- archive converted leads out of the active set
- copy pre-conversion notes and activities onto the new durable records
- move open relationship-building tasks primarily to the new `Opportunity`
- preserve provenance back to the source `Lead`

Acceptance criteria:
- conversion creates the expected records
- converted leads are archived and marked `converted`
- relevant tasks, notes, and activities are carried forward
- autonomous conversion is allowed only when a specific opportunity is already clear
- interactive mode requires approval where expected

## 4. Replace Notes-as-Inbox with a First-Class Inbox

**Title**
`Replace Notes-as-inbox with a first-class Inbox workflow`

**Labels**
`enhancement`

**Body**
Introduce `Inbox/` as the raw capture layer and deprecate the current Notes-as-inbox behavior.

Scope:
- add `Inbox/` structure and template
- define Inbox item statuses such as `new`, `processing`, `processed`, and `ignored`
- implement processing flow that can emit:
  - `Note`
  - `Activity`
  - `Task`
  - `Lead`
  - `Contact`
  - `Account`
  - `Opportunity`
- delete or remove processed Inbox items from the active queue by default
- support both interactive and autonomous processing modes

Acceptance criteria:
- raw capture no longer depends on `Notes/`
- a single Inbox item can yield multiple durable outputs
- processed Inbox items do not linger in the active queue by default
- event-based inputs produce `Activity` records during processing

## 5. Implement First-Class Notes and Updated Activity Linking

**Title**
`Implement first-class Notes and updated Activity linking model`

**Labels**
`enhancement`

**Body**
Refactor Notes and Activities into distinct but linked first-class record types under the v4 memory model.

Scope:
- make `Note` a durable record type with its own schema and creation flow
- support one `primary-parent` plus optional `secondary-links`
- apply the same linking pattern to `Activity`
- enforce primary parent precedence:
  1. `Opportunity`
  2. `Contact`
  3. `Account`
- allow note-only records for strategic context not tied to a discrete event
- ensure event-derived records produce `Activity`

Acceptance criteria:
- Notes and Activities follow the shared linking model
- Notes can exist without Activities when appropriate
- Activities are created for real events and interactions
- both record types align with `docs/schema-addendum-v4-core-records.md`

## 6. Build the Unified Relationship Memory Layer

**Title**
`Build the unified relationship memory layer for key records`

**Labels**
`enhancement`

**Body**
Make the vault behave like a trustworthy memory system by assembling summaries and relationship context from linked records.

Scope:
- generate relationship summaries for key records
- combine notes, activities, tasks, conversions, and recent signals into one memory view
- support drill-down from AI summary into underlying records
- distinguish observed facts from inferred conclusions in the implementation model

Acceptance criteria:
- core records can produce stable memory summaries
- users and agents can drill down into the underlying record graph on demand
- memory assembly works across converted and pre-conversion states

## 7. Implement Workspace Sync for Gmail and Calendar

**Title**
`Implement real workspace sync for Gmail and Calendar`

**Labels**
`enhancement`

**Body**
Replace the current `sync-workspace` specification-only state with an implemented Gmail/Calendar ingestion flow aligned to v4.

Scope:
- implement Gmail ingestion for interaction detection and lead discovery
- implement Calendar ingestion for meeting-driven activities and recency updates
- match workspace signals to known entities
- create or propose new `Lead` records based on confidence thresholds
- support autonomous creation only for high-confidence cases
- support review queue behavior for ambiguous cases
- use staging/state files for deduplication and provenance

Acceptance criteria:
- workspace sync runs as code, not only as documentation
- Gmail and Calendar materially update relationship memory
- high-confidence signals can create `new` leads when autonomous capture is enabled
- ambiguous signals route to review

## 8. Upgrade the Dashboard to the v4 Relationship-First Model

**Title**
`Upgrade the dashboard to the v4 relationship-first model`

**Labels**
`enhancement`

**Body**
Refactor dashboard generation so the home view aligns with the v4 PRD rather than primarily reflecting file activity.

Scope:
- prioritize sections in this order:
  1. relationships needing attention
  2. recently active / heating up relationships
  3. qualified leads / near-conversion
  4. recommended next actions
- expose separate visible signals such as:
  - `warmth`
  - `velocity`
  - `priority`
- rank with an internal composite attention score
- allow important qualified leads into main relationship sections
- include Inbox triage and note visibility where appropriate

Acceptance criteria:
- the dashboard is relationship-first rather than chronology-first
- ranking uses composite attention logic
- visible signals are distinct from the hidden composite score
- important qualified leads can surface in the main dashboard

## 9. Migrate Legacy Notes and Clean Up Obsolete v3 Flows

**Title**
`Migrate legacy Notes usage and clean up obsolete v3 flows`

**Labels**
`enhancement`

**Body**
Prepare the repo and sample vault behavior for a clean v3-to-v4 transition.

Scope:
- define migration rules for legacy `Notes/`
- identify which legacy notes remain `Note` records versus old Inbox artifacts
- update README, GEMINI instructions, and skill docs
- remove or deprecate obsolete Notes-as-inbox instructions
- add sample data or fixtures for v4 entities

Acceptance criteria:
- documentation matches actual v4 behavior
- legacy notes are handled by an explicit migration strategy
- obsolete conceptual instructions are removed or clearly deprecated

## 10. Narrow Dashboard Bookkeeping Commit Scope

**Title**
`Narrow dashboard bookkeeping commit scope in update-dashboard workflow`

**Labels**
`enhancement`

**Body**
The current dashboard automation commits the entire data repo with `git add .`, which can sweep in unrelated files. Narrow the bookkeeping scope to only the generated artifacts and intended changes.

Scope:
- update dashboard/intelligence bookkeeping logic to avoid broad `git add .`
- commit only intended generated files or explicitly tracked outputs
- preserve auditability while reducing accidental commits

Acceptance criteria:
- dashboard runs do not commit unrelated files by default
- generated outputs still commit cleanly
- commit behavior remains consistent with the repo’s automation model
