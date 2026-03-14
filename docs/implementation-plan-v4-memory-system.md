# Implementation Plan: CRM v4.0 – The Memory System

**Status:** Draft
**Depends On:** [prd-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/prd-v4-memory-system.md)
**Goal:** Translate the v4 PRD into an executable implementation sequence for the existing markdown/git vault architecture

## 1. Implementation Objective
Deliver CRM v4.0 as an evolution of the current `crm-logic` system, preserving the private markdown/git vault as the source of truth while introducing:
- first-class `Lead`
- first-class `Note`
- dedicated `Inbox`
- relationship-first dashboarding
- stronger AI memory and provenance behavior
- day-one Google Workspace integration as an input and sync layer

This plan is intentionally staged. The goal is to reduce schema churn, protect trust in the vault, and avoid breaking existing v3 workflows while v4 foundations are introduced.

## 2. Guiding Constraints
- The markdown/git vault remains the system of record.
- The product remains single-operator and AI-first.
- Existing data should be migrated with minimal destructive rewriting.
- New automation must remain auditable through git history and explicit logs.
- Interactive and autonomous modes must both be supported.
- Work should be sequenced so the system remains usable between milestones.

## 3. Major Workstreams
1. Information architecture and schema design
2. Vault structure and migration strategy
3. Core entity workflows
4. Inbox and processing pipeline
5. Relationship memory and timeline model
6. Google Workspace ingestion and sync
7. Dashboard and prioritization layer
8. AI trust, provenance, and summarization
9. Backward compatibility, migration, and rollout

## 4. Recommended Delivery Sequence

### Phase 0: Architecture and Design Freeze
Objective: lock the minimum viable v4 model before code changes spread across skills and scripts.

Deliverables:
- final schema direction for `Lead`, `Inbox`, `Note`, `Activity`, and core link conventions
- folder structure decision for new first-class entities
- parent-linking conventions for `Note` and `Activity`
- conversion and archival rules for `Lead`
- migration principles for existing `Notes/`

Exit criteria:
- no major open question remains about record responsibilities
- implementation can proceed without re-litigating core product boundaries

### Phase 1: Vault Structure and Schemas
Objective: add the new primitives to the vault model without yet depending on full automation.

Deliverables:
- new directories and templates for `Leads/`, `Inbox/`, and first-class `Notes/`
- updated templates for `Contacts/`, `Accounts/`, `Opportunities/`, `Tasks/`, and `Activities/`
- schema conventions for:
  - primary parent
  - secondary links
  - provenance/source
  - owner
  - lead-source
  - status and lifecycle fields
- updated docs for entity definitions and record semantics

Key implementation areas:
- `templates/`
- skill docs under `.gemini/skills/`
- schema assumptions in Python scripts

Exit criteria:
- new records can be manually created in valid v4 format
- existing scripts do not catastrophically fail when new directories exist

### Phase 2: Lead Lifecycle Foundations
Objective: implement `Lead` as a first-class entity and define the path from signal to conversion.

Deliverables:
- `create-lead` skill or equivalent workflow
- lead status support:
  - `new`
  - `prospect`
  - `engaged`
  - `qualified`
  - `converted`
  - `disqualified`
- conversion workflow from `Lead -> Contact + Account + Opportunity`
- support for:
  - sparse `new` leads
  - person-only and company-only early-stage leads
  - qualified-lead validation before conversion
  - revival from `disqualified`
  - lead archival after conversion

Key implementation areas:
- new lead skill definitions
- conversion helper logic
- migration-safe link generation
- dashboard filtering rules

Exit criteria:
- leads can be created, updated, disqualified, revived, and converted
- converted leads no longer pollute the active lead set

### Phase 3: Inbox as Raw Capture Layer
Objective: replace the old “Notes as inbox” behavior with a dedicated temporary intake queue.

Deliverables:
- `Inbox/` folder model
- Inbox item schema and template
- processing workflow that can emit:
  - `Note`
  - `Activity`
  - `Task`
  - `Lead`
  - `Contact`
  - `Account`
  - `Opportunity`
- default deletion or removal of processed Inbox items
- interactive and autonomous processing modes

Key implementation areas:
- new processing skill or enhancement to existing “process note” behavior
- deprecation plan for old Notes inbox flow
- task/activity/note branching logic

Exit criteria:
- raw capture no longer depends on `Notes/`
- one Inbox item can yield multiple durable outputs

### Phase 4: First-Class Notes and Activity Linking
Objective: establish durable context and event records as distinct but connected entities.

Deliverables:
- first-class `Note` schema and creation workflow
- support for:
  - one primary parent
  - optional secondary links
  - timeline inclusion
  - note-only records for non-event context
- updated `Activity` model with the same parent-linking pattern
- precedence rule implementation:
  - `Opportunity`
  - `Contact`
  - `Account`

Key implementation areas:
- creation skills
- timeline aggregation logic
- dashboard/context rendering
- migration of any current assumptions that Notes are unstructured overflow

Exit criteria:
- event-based inputs create `Activity`
- durable context can exist as `Note`
- both are queryable through relationship memory views

### Phase 5: Relationship Memory Layer
Objective: make the vault behave like a trustworthy memory system rather than a loose collection of files.

Deliverables:
- unified relationship summary generation for key records
- memory assembly logic combining:
  - activities
  - notes
  - tasks
  - conversions
  - recent workspace signals
- drill-down support from summary to underlying source records
- provenance-aware summaries that distinguish observations from inference

Key implementation areas:
- dashboard generation
- summary generation helpers
- intelligence engine refactor or extension

Exit criteria:
- core records can produce stable, useful summaries from underlying evidence
- users can drill down without ambiguity

### Phase 6: Google Workspace Ingestion
Objective: move from partial intent/specification to real workspace-driven memory capture.

Deliverables:
- implemented `sync-workspace` flow, not just skill documentation
- Gmail ingestion for:
  - interaction detection
  - known-entity matching
  - new lead suggestions or autonomous creation
- Calendar ingestion for:
  - meeting-derived activities
  - recency updates
  - new lead clues
- alignment with existing Google Tasks sync
- interaction state cache and deduplication logic

Key implementation areas:
- `sync-workspace`
- staging/state files
- Gmail/Calendar matching logic
- AI classification thresholds for lead creation

Exit criteria:
- workspace signals materially update relationship memory
- high-confidence signals can create `new` leads in autonomous mode
- low-confidence signals are routed to review

### Phase 7: Relationship Dashboard v4
Objective: make the home view align with the PRD’s relationship-first model.

Deliverables:
- top-level dashboard sections prioritized as:
  1. relationships needing attention
  2. recently active / heating up relationships
  3. qualified leads / near-conversion
  4. recommended next actions
- visible signals for:
  - warmth
  - velocity
  - priority
- internal composite attention score for ranking
- inclusion of important qualified leads alongside converted entities
- Inbox triage and recent-note visibility where appropriate

Key implementation areas:
- `update-dashboard.py`
- intelligence scoring
- ranking heuristics
- markdown rendering of dashboard sections

Exit criteria:
- the default dashboard reflects relationship priority, not just recent file activity
- the dashboard helps the user reconstruct context and decide where to focus

### Phase 8: Migration and Cleanup
Objective: move from v3 behavior to v4 cleanly without leaving conceptual ambiguity in the repo.

Deliverables:
- migration scripts or guided manual migration notes
- handling for legacy `Notes/` used as inbox
- documentation updates across:
  - `README.md`
  - `GEMINI.md`
  - skill docs
  - templates
- removal or deprecation of obsolete instructions
- test fixtures or sample vault examples for v4 entities

Exit criteria:
- repo documentation matches actual behavior
- legacy patterns are either supported intentionally or removed

## 5. Workstream Details

### 5.1 Information Architecture and Schema Design
This should happen early and be explicit. The biggest risk to v4 is introducing new concepts without stable conventions.

Must define:
- minimum viable frontmatter for `Lead`
- minimum viable frontmatter for `Inbox Item`
- minimum viable frontmatter for `Note`
- parent/secondary link conventions
- provenance conventions
- archival conventions

Recommended output:
- a schema addendum document in `docs/`
- updated templates that embody the schema directly

### 5.2 Vault Structure and Migration Strategy
The current vault model must evolve safely. Do not assume that all historic data is clean or structurally consistent.

Must address:
- where archived leads live
- how processed Inbox items are removed
- whether existing `Notes/` content maps to `Note`, `Inbox`, or `Activity`
- how timeline assembly works for old records with incomplete links

### 5.3 Core Entity Workflows
Each new or changed entity needs an explicit lifecycle workflow, not just a template.

Must cover:
- create
- update
- link
- summarize
- convert or archive when applicable

Highest priority workflows:
- lead creation and conversion
- inbox processing
- note creation
- activity creation from events

### 5.4 Google Workspace Integration
This is the highest-value automation stream and the largest gap between current intent and actual implementation.

Must solve:
- Gmail thread retrieval and parsing
- Calendar event ingestion
- entity matching
- lead creation thresholds
- deduplication
- autonomous vs interactive branching

This should likely be implemented incrementally:
1. read-only signal ingestion
2. suggestions and review queue
3. autonomous creation for high-confidence cases

### 5.5 Relationship Scoring and Dashboard Logic
Existing warmth and velocity concepts should be preserved but repositioned.

Must evolve toward:
- visible component signals
- composite hidden ranking
- inclusion of qualified leads
- support for commercial value when explicit or inferred

### 5.6 AI Trust and Provenance
The system should optimize for trust without overburdening the main interface.

Must support:
- concise summaries
- on-demand drill-down
- distinction between observed data and inferred interpretation
- auditable record mutation

## 6. Technical Strategy Recommendations
- Reuse and extend the existing script-first architecture before introducing larger framework changes.
- Centralize frontmatter parsing and normalization into shared helpers instead of duplicating logic in each script.
- Treat schema validation as a first-class implementation concern early.
- Avoid broad `git add .` style bookkeeping in automation where narrower commit scopes are possible.
- Design staging/state files explicitly for sync and provenance rather than letting them emerge ad hoc.

## 7. Suggested Milestone Breakdown

### Milestone A: v4 Foundations
- schema docs and templates
- new folders and record types
- backward-compatible parser updates

### Milestone B: Leads and Inbox
- lead entity
- conversion workflow
- inbox processing and removal of notes-as-inbox dependency

### Milestone C: Notes, Activities, and Memory
- note/activity linking
- unified memory assembly
- initial timeline behavior

### Milestone D: Workspace-Powered Memory
- real `sync-workspace` implementation
- autonomous and interactive modes
- signal-driven lead creation

### Milestone E: Relationship Dashboard v4
- new prioritization logic
- composite scoring
- relationship-first home view

### Milestone F: Migration and Hardening
- data migration
- documentation alignment
- cleanup of obsolete flows

## 8. Dependencies and Preconditions
- stable v4 PRD
- access to the private vault for migration testing
- Google Workspace auth and testable sync environment
- representative sample data covering:
  - leads
  - contacts
  - accounts
  - opportunities
  - notes
  - activities
  - inbox items

## 9. Key Risks During Implementation
- schema fragmentation across templates and scripts
- accidental corruption of existing vault data during migration
- over-eager autonomous creation of leads or opportunities
- dashboard complexity outpacing actual memory quality
- mismatch between PRD terminology and implemented record behavior
- partial rollout leaving old Notes inbox behavior alive too long

## 10. Open Design Items to Resolve During Implementation
- exact frontmatter for `Lead`
- exact frontmatter for `Inbox Item`
- exact frontmatter for `Note`
- timeline rendering rules for migrated legacy content
- whether `Opportunity` needs subtype fields
- what level of provenance is stored directly on records versus in derived/staging artifacts

## 11. Recommended Next Step
Before coding, create a short schema addendum for:
- `Lead`
- `Inbox Item`
- `Note`
- `Activity`

That should be the design artifact immediately following this implementation plan. It is narrow enough to resolve quickly and concrete enough to unblock the first real code changes.
