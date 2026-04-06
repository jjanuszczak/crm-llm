# CRM Opportunity Manager Spec

## Status

Draft for review.

This document defines the intended behavior, scope, workflow boundaries, and implementation shape for a future top-level skill:

- `crm-opportunity-manager`

It is a planning artifact only. It does not imply that the skill, scripts, or sub-workflows are implemented yet.

## Purpose

`crm-opportunity-manager` should be the top-level operating skill for active commercial work.

It should own the user-facing question:

- "What should exist, change, or happen next for this opportunity?"

This skill should manage the lifecycle of an `Opportunity` from creation through active execution to won, lost, or stale/archived states.

It should sit above narrower utility actions such as:

- create opportunity
- create task
- create activity
- create note
- update dashboard

Those utilities should support the workflow, not define it.

## Why This Should Be Top-Level

This skill should be top-level because:

- `Opportunity` is the operational center of gravity when active work exists.
- post-conversion execution is the largest current workflow gap in the repo.
- stage movement, stakeholder linkage, milestone management, and close logic are judgment-heavy.
- opportunity work spans multiple record types:
  - `Opportunity`
  - `Account`
  - `Organization`
  - `Contact`
  - `Task`
  - `Activity`
  - `Note`
- users are likely to ask directly in opportunity terms:
  - "Create an opportunity"
  - "Advance this opportunity"
  - "Mark this lost"
  - "What are the next steps here?"

## Scope

The skill should own:

- opportunity creation
- parent context selection and validation
- stakeholder and influencer assignment
- stage and probability updates
- milestone and next-step management
- close-won and close-lost handling
- stale opportunity review and archive decisions
- spawning follow-up `Tasks`, `Activities`, and `Notes`

The skill should not own:

- lead classification or conversion policy
  - that remains under `crm-lead-manager`
- inbox triage
  - that remains under `crm-inbox-manager`
- broad relationship-health review across many records
  - that belongs under `crm-relationship-review`
- schema migrations or path repair
  - that belongs under `crm-schema-maintenance`

## Canonical Opportunity Model

This skill should use the canonical opportunity model in [schema-spec.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-spec.md).

Required or central fields:

- `id`
- `opportunity-name`
- `owner`
- `account`
- `organization`
- `primary-contact`
- `opportunity-type`
- `is-active`
- `stage`
- `commercial-value`
- `close-date`
- `probability`
- `product-service`
- `influencers`
- `source`
- `source-ref`
- `source-lead` when applicable
- `lost-at-stage`
- `lost-reason`
- `lost-date`
- `date-created`
- `date-modified`

The skill should treat:

- `commercial-value` as canonical
- `deal-value` as compatibility-only

The skill should not introduce deprecated opportunity fields.

## Operating Assumptions

- Active work should usually anchor new `Notes`, `Activities`, and `Tasks` primarily to the `Opportunity`.
- `Organization` owns stable identity.
- `Account` owns the commercial relationship wrapper.
- `Contact` owns person identity.
- `Opportunity` owns the active execution path.

## When To Use

Use `crm-opportunity-manager` when the user wants to:

- create a new opportunity under an existing relationship
- determine whether an opportunity should exist yet
- refine opportunity structure after lead conversion
- assign or revise stakeholders
- change stage, probability, or value
- review what is missing for execution
- mark an opportunity won or lost
- archive or reopen a stale opportunity
- create follow-up tasks or activities from opportunity context

## User-Facing Questions It Should Answer

Examples:

- "Create a new opportunity for Example Company."
- "Should this account already have an opportunity?"
- "Advance this from discovery to proposal."
- "What stakeholders are missing?"
- "Mark this opportunity lost and capture the reason."
- "What tasks should exist for this opportunity?"
- "This opportunity feels stale. What should we do?"

## Workflow

### 1. Orient to current context

The skill should first read:

- `crm-data/index.md`
- the target `Opportunity` if one exists
- linked `Account`, `Organization`, and `Contact` records
- recent `Tasks`, `Activities`, and `Notes` attached to that opportunity
- `crm-data/log.md` when recent operational history matters

### 2. Decide whether the user needs:

- create
- structure/update
- execute/follow-up
- close
- archive/revive

### 3. Validate parent context

Before creating or materially updating an opportunity, the skill should confirm:

- which `Organization` is involved
- whether an `Account` exists and should anchor the opportunity
- which `Contact` is primary
- whether there is a `Lead` provenance link

If context is ambiguous, the skill should resolve:

1. `Account`
2. `Organization`
3. `Primary Contact`

If active commercial work is not yet real, the skill should explicitly say the relationship may still belong in `Lead` or `Contact` state instead of forcing opportunity creation.

### 4. Apply the relevant sub-workflow

#### A. Create opportunity

The skill should:

- choose canonical parent links
- choose `opportunity-type`
- choose a name in canonical hyphen-safe form for the filename while preserving a human-readable `opportunity-name`
- default:
  - `stage=discovery`
  - `probability=10`
  - `is-active=true`
- populate provenance fields
- optionally seed stakeholder and milestone sections from available context

#### B. Structure or enrich opportunity

The skill should support:

- assigning or revising `primary-contact`
- adding `influencers`
- setting `product-service`
- adjusting `commercial-value`
- clarifying close target date
- normalizing links to `Account`, `Organization`, and `Deal`

#### C. Advance execution

The skill should support:

- stage changes
- probability updates
- next-step creation
- milestone management
- task spawning
- activity creation from completed interactions
- note creation for durable strategy or context

#### D. Close won

The skill should:

- set terminal stage
- set final `probability`
- set `is-active=false`
- set or confirm `close-date`
- create follow-up tasks only if post-close work exists
- preserve the opportunity as durable history

#### E. Close lost

The skill should:

- set terminal stage
- set `is-active=false`
- populate:
  - `lost-at-stage`
  - `lost-reason`
  - `lost-date`
- preserve record history
- avoid deleting the opportunity

#### F. Archive stale opportunity

The skill should support a stale-path decision when:

- there has been no meaningful movement for a long window
- no open task or recent activity supports continued active status
- the opportunity should remain historical but not operationally active

This should usually mean:

- `is-active=false`
- retain history
- optionally create a follow-up reminder task if the user wants a later recheck

### 5. Explain the outcome

The skill should tell the user:

- what changed
- why
- what related records were created or updated
- what next action is recommended

## Proposed Sub-Workflows

The skill should formally include:

- create opportunity
- choose parent account/contact/organization context
- assign stakeholders and influencers
- update stage and probability
- manage next steps and milestones
- mark won
- mark lost
- archive stale opportunity
- spawn follow-up tasks and activities

## State Model

This skill should use the current canonical `stage` field and should not invent a second status system for opportunities.

Initial implementation should tolerate existing live stages but guide toward a stable working set such as:

- `discovery`
- `qualified`
- `proposal`
- `negotiation`
- `closed-won`
- `closed-lost`

If the repo wants stricter stage semantics later, they should be defined in schema and then enforced here.

`is-active` should remain the binary operational flag.

## Implementation Shape

Recommended shape:

- top-level skill:
  - `.gemini/skills/crm-opportunity-manager/SKILL.md`
- canonical implementation script:
  - `.gemini/skills/crm-opportunity-manager/scripts/opportunity_manager.py`
- compatibility wrapper if needed:
  - `scripts/opportunity_manager.py`
- supporting references:
  - `.gemini/skills/crm-opportunity-manager/references/lifecycle.md`
  - `.gemini/skills/crm-opportunity-manager/references/cli-patterns.md`
  - `.gemini/skills/crm-opportunity-manager/references/close-rules.md`
  - `.gemini/skills/crm-opportunity-manager/references/stakeholder-model.md`

## CLI Surface

Initial command surface should likely look like:

- `create`
- `update`
- `set-stage`
- `set-probability`
- `assign-stakeholders`
- `spawn-task`
- `spawn-activity`
- `mark-won`
- `mark-lost`
- `archive-stale`
- `review`

Illustrative examples:

```bash
python3 scripts/opportunity_manager.py create \
  --account "Accounts/Example-Company" \
  --organization "Organizations/Example-Company" \
  --primary-contact "Contacts/Jane-Doe" \
  --name "Example Company - Strategic Advisory - 2026" \
  --opportunity-type advisory \
  --source manual
```

```bash
python3 scripts/opportunity_manager.py set-stage \
  "Opportunities/Example-Company-Strategic-Advisory-2026" \
  --stage proposal \
  --probability 40
```

```bash
python3 scripts/opportunity_manager.py mark-lost \
  "Opportunities/Example-Company-Strategic-Advisory-2026" \
  --reason "budget shifted" \
  --lost-date 2026-05-10
```

## Policy Rules

The skill should follow repo-wide rules:

- resolve `CRM_DATA_PATH` dynamically
- use canonical templates and frontmatter conventions
- keep filenames hyphen-separated and punctuation-safe
- update `crm-data/index.md` after successful mutation workflows
- append to `crm-data/log.md` for mutation workflows
- prefer one workflow-level log entry for multi-record mutations

## Relationship To Existing Skills

### Reuses

- `create-opportunity`
- `create-task`
- `create-activity`
- `create-note`
- `update-dashboard`

### Supersedes as top-level abstraction

Over time, this skill should reduce direct top-level reliance on:

- raw `create-opportunity`
- ad hoc manual opportunity edits

Those should become sub-workflow helpers inside an opportunity-centered operator flow.

## Non-Goals For First Version

The first version should not try to do all of the following:

- automatic close prediction
- automatic stakeholder scraping
- bulk portfolio-wide opportunity review
- universal stage normalization across the vault
- CRM-wide dashboard regeneration policy beyond what existing scripts already support

Those can be later enhancements.

## Acceptance Criteria For Initial Version

The first useful version should be approved only if it can:

1. create a canonical opportunity linked to account, organization, and primary contact
2. update stage and probability safely
3. assign influencers and stakeholders
4. mark won and mark lost with proper close bookkeeping
5. spawn follow-up tasks or activities from opportunity context
6. update `index.md` and append `log.md`
7. explain decisions and outputs clearly at the workflow level

## Open Questions

Questions to resolve before implementation:

1. What exact working stage vocabulary should be enforced versus merely tolerated?
2. Should `review` be read-only, or allowed to stage edits and task suggestions?
3. Should `mark-won` create any automatic downstream records, or only update the opportunity?
4. What stale threshold should `archive-stale` use by default?
5. Should stakeholder roles remain mostly in body prose for now, or be expanded in structured frontmatter?
