# Proposed Skill Map

## Purpose

This document proposes a skill map for the repo.

It is a planning artifact only. It does not imply that all listed skills should be implemented immediately, and it does not change current repo behavior.

The goal is to define:
- which workflows deserve first-class top-level skills
- which workflows should be sub-workflows under those skills
- how the repo should be organized around major CRM operating motions

## Design Principle

A workflow should be a **top-level skill** when it:
- is a major operator decision loop
- has multiple branching outcomes
- touches multiple entity types
- carries non-trivial judgment
- is likely to be invoked directly by a user

A workflow should be a **sub-workflow** when it:
- mostly exists to support a larger operator motion
- is narrower and more procedural
- should usually be entered through a parent workflow
- shares context, policy, and review logic with a parent skill

## Proposed Top-Level Skills

### 1. `crm-ingest-gws`

Purpose:
- ingest Gmail and Calendar activity into staged CRM review queues and safe activity writes

Why top-level:
- it is the front door for ambient relationship intake
- it drives contact discovery, lead decisions, opportunity suggestions, and task suggestions
- it has a distinct review workflow and automation policy

Proposed sub-workflows:
- source harvesting
- event normalization
- company/contact/lead resolution
- activity auto-write
- contact discovery review
- lead decision review
- opportunity suggestion review
- task suggestion review
- noise review
- meeting-notes enrichment

### 2. `crm-lead-manager`

Purpose:
- manage the full lead lifecycle from identification to conversion

Why top-level:
- lead state is a first-class CRM operating model
- conversion is a major workflow with branching outputs
- qualification and conversion require judgment, not just data entry

Proposed sub-workflows:
- create lead
- enrich lead
- set lead status
- validate qualification
- revive disqualified lead
- suggest conversion path
- convert to commercial path
- convert to relationship-only path

### 3. `crm-opportunity-manager`

Purpose:
- create, structure, advance, and close opportunities

Why top-level:
- opportunities are the operational center of gravity when active work exists
- this is a major commercial workflow distinct from lead conversion
- stage movement, stakeholder linkage, and close logic are complex enough to stand alone

Proposed sub-workflows:
- create opportunity
- choose parent account/contact/organization context
- assign stakeholders and influencers
- update stage and probability
- manage next steps and milestones
- mark won
- mark lost
- archive stale opportunity
- spawn follow-up tasks and activities

### 4. `crm-relationship-review`

Purpose:
- review the health, momentum, and next actions for an existing relationship

Why top-level:
- this is the core “operating the book” workflow
- it spans accounts, contacts, opportunities, activities, tasks, and notes
- it is broader than dashboard generation and more decision-oriented

Proposed sub-workflows:
- review account/contact/opportunity cluster
- assess warmth and velocity
- identify stale relationships
- identify missing stakeholders
- identify missing follow-ups
- recommend next actions
- prepare relationship brief

### 5. `crm-task-manager`

Purpose:
- manage explicit CRM next actions from creation through closeout

Why top-level:
- tasks are a major execution workflow
- they interact with opportunities, leads, contacts, and ingest
- task hygiene materially affects dashboard quality and operational clarity

Proposed sub-workflows:
- create task
- classify committed vs suggested follow-up
- re-parent task
- complete task
- bulk review stale tasks
- task closeout from later activities

### 6. `crm-contact-manager`

Purpose:
- create, expand, normalize, and maintain people records across relationships

Why top-level:
- contact expansion is a major workflow in this CRM
- dual-role cases, stakeholder addition, and context reassignment recur often
- this is no longer just “create contact”

Proposed sub-workflows:
- create contact
- attach contact to existing relationship
- detect dual-role contact
- upgrade stakeholder context
- merge duplicate contacts
- normalize person/account links

### 7. `crm-inbox-manager`

Purpose:
- process raw capture into durable CRM records

Why top-level:
- inbox processing is a distinct operator workflow
- it is broader than creating a note or activity
- it is the bridge between unstructured capture and structured CRM memory

Proposed sub-workflows:
- triage inbox item
- convert to note
- convert to activity
- convert to task
- multi-output processing
- assign primary parent
- archive inbox item

### 8. `crm-memory-manager`

Purpose:
- generate and maintain the derived memory layer of the CRM

Why top-level:
- this covers dashboard, intelligence, and relationship memory outputs
- these are operator-facing synthesis products, not just utilities
- review of derived outputs is a meaningful workflow in itself

Proposed sub-workflows:
- update dashboard
- update intelligence
- update relationship memory
- inspect telemetry gaps
- validate surfaced priorities

### 9. `crm-matchmaker`

Purpose:
- match deals, opportunities, and accounts for brokerage or advisory use cases

Why top-level:
- this is a distinct strategic workflow, not just a report
- it has different logic than general relationship review
- it is directly tied to the repo’s brokerage and matchmaking use case

Proposed sub-workflows:
- match deal to account
- match account to deal
- rank match strength
- review warm paths
- generate brokerage suggestions

### 10. `crm-schema-maintenance`

Purpose:
- normalize, migrate, and repair vault structure and references

Why top-level:
- schema evolution and migration are recurring realities in this repo
- these tasks are risky and deserve explicit workflow boundaries
- they are different from day-to-day CRM operation

Proposed sub-workflows:
- migrate schema versions
- rewrite references
- normalize record paths
- organize timestamped entities
- validate frontmatter conventions
- identify compatibility-field drift

## Proposed Supporting Skills

These are narrower skills that may remain standalone utilities or become sub-workflows behind top-level skills.

### Record Creation Skills
- `create-activity`
- `create-task`
- `create-note`
- `create-lead`
- `create-organization`
- `create-inbox-item`

Role in the map:
- mostly supporting sub-workflows
- useful as direct utilities, but not the best top-level abstraction for daily CRM operations

### Sync / Utility Skills
- `sync-google-tasks`
- `manage-intelligence`

Role in the map:
- some may remain standalone operational commands
- some should increasingly be treated as sub-workflows under broader top-level skills like `crm-ingest-gws` or `crm-memory-manager`

## Proposed Hierarchy

### Intake Layer
- `crm-ingest-gws`
- `crm-inbox-manager`

### Relationship Formation Layer
- `crm-lead-manager`
- `crm-contact-manager`

### Commercial Execution Layer
- `crm-opportunity-manager`
- `crm-task-manager`

### Relationship Operations Layer
- `crm-relationship-review`
- `crm-memory-manager`

### Strategic / Brokerage Layer
- `crm-matchmaker`

### Maintenance Layer
- `crm-schema-maintenance`

## How I Would Define Top-Level vs Sub-Workflow Boundaries

### Top-level skill boundary

A top-level skill should own:
- the user-facing operating question
- the review sequence
- the policy and judgment rules
- the branching logic
- the handoff to narrower creation or update utilities

Example:
- `crm-lead-manager` should own “what stage is this relationship in and how should it convert?”
- it should call or embed narrower record-creation steps rather than forcing the user to think in raw file operations

### Sub-workflow boundary

A sub-workflow should own:
- one bounded action inside a parent workflow
- a clear input and output
- a narrower record mutation pattern

Example:
- “create activity from ingested email”
- “attach contact to existing lead context”
- “mark opportunity lost”

These are important, but they are not the main operator question.

## Recommended Priorities

If the repo formalizes this map gradually, I would prioritize in this order:

1. `crm-opportunity-manager`
2. `crm-relationship-review`
3. `crm-task-manager`
4. `crm-contact-manager`
5. `crm-memory-manager`
6. `crm-schema-maintenance`

Reason:
- `crm-ingest-gws` and `crm-lead-manager` are already being actively clarified
- the next major gap is the workflow after conversion, not before it
- opportunity execution and relationship review are the biggest missing first-class operating skills

## Current Repo Mapping

Approximate current state:
- `crm-ingest-gws`: partially formalized
- `crm-lead-manager`: formalized
- inbox processing: partially formalized
- dashboard/intelligence refresh: formalized but utility-oriented
- record creation: formalized at utility level
- opportunity management: not yet formalized as a coherent skill
- relationship review: not yet formalized
- contact management: not yet formalized
- schema maintenance: implemented through scripts, not yet clearly modeled as a workflow family

## Recommendation

The repo should evolve toward:
- fewer narrow top-level “create-X” mental models
- more operator-centered top-level skills
- narrower creation/update actions treated as sub-workflows or helper utilities

That would make the system easier to operate around real CRM motions:
- intake
- qualification
- conversion
- execution
- review
- maintenance
