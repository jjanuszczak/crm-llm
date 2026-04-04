# Gemini Context: CRM Logic

## Purpose

This repo is the logic layer for a private AI-first personal CRM.

The source of truth is the markdown vault at `CRM_DATA_PATH`, not this repo itself. This repo contains:
- templates for canonical record creation
- scripts that read, write, and synthesize the vault
- Gemini skill instructions for operational workflows
- examples and schema docs for onboarding and maintenance

The system is optimized for one principal operator doing relationship-led advisory, consulting, fundraising, brokerage, and related operator work.

## Start Here

If you are new to the project, read in this order:

1. `docs/schema-spec.md`
2. `README.md`
3. `crm-data/DASHBOARD.md`
4. `crm-data/RELATIONSHIP_MEMORY.md`
5. `crm-data/INTELLIGENCE.md`

Then inspect the relevant `Organization`, `Account`, `Contact`, and `Opportunity` records for the relationship you are working on.

## Core Mental Model

Think in two layers:

- `crm-logic/`
  - public-friendly logic, templates, scripts, and skills
- `crm-data/`
  - private vault and operational system of record

This is a local-first, markdown-native, git-auditable memory system. Trust matters more than automation volume.

## Environment

Always resolve `CRM_DATA_PATH` dynamically from `.env` or the environment.

Typical local setup:

```text
CRM_DATA_PATH=./crm-data
```

Do not assume:
- the vault is checked into the main repo
- the vault is fully normalized
- all records follow the latest templates perfectly
- every write should be committed automatically

## Current Canonical Entity Model

The canonical schema is in `docs/schema-spec.md`. Use that file as the source of truth for fields and status labels.

### Organizations
- Stable market entities
- Own identity, classification, investor profile fields, and observed signals such as `last-contacted`

### Accounts
- Commercial relationship wrappers around `Organizations`
- Own relationship lifecycle and `strategic-importance`

### Contacts
- Durable person records
- Usually link to an `Account`, and optionally to a `Deal`

### Leads
- Pre-conversion records
- Default conversion path:
  - `Lead -> Organization + Contact + Account + Opportunity`

### Opportunities
- Concrete commercial or strategic engagements
- This is the operational center of gravity when active work exists

### Deals
- Fundraising inventory objects
- Still stored under `Deal-Flow/` in the current vault, even though the conceptual entity name is `Deal`

### Notes
- Durable strategic or contextual memory
- Not raw intake

### Activities
- Real events or interactions
- Emails, meetings, calls, analysis, and other event records

### Tasks
- Explicit next actions

### Inbox
- Temporary raw capture
- Should usually be processed into durable records and then cleared

## Canonical vs Calculated vs Deprecated

`docs/schema-spec.md` explicitly marks:
- `Canonical`
- `Calculated`
- `Compatibility`
- `Deprecated`

Follow those labels.

Important practical rules:
- Prefer canonical fields for all new writes
- Do not add deprecated fields to new records
- Calculated fields are telemetry or cache, not business truth
- Compatibility fields may still exist in live vault data and must be tolerated by readers

## What Is Canonical Right Now

### Account model
- `Organization` is first-class
- `Account` is relationship-layer, not identity-layer
- New Account writes should not include old identity fields like `company-name`, `type`, `industry`, `size`, `investment-mandate`, or `check-size`

### Opportunity model
- `commercial-value` is canonical
- `deal-value` is compatibility-only
- `organization` is canonical on opportunities
- `opportunity-type` is canonical
- Investor mandate and check-size do not belong on opportunities
- Deal fundraising fields do not belong on opportunities

### Contact model
- `full-name` is canonical
- `full--name` is legacy-only

### Path reality
- `Deal-Flow/` is still the live deal path in the vault
- Readers should tolerate legacy path and field shapes

## Current Vault Reality

The vault has already gone through a structural cleanup. Current state:

- Non-commercial legacy Account shims were removed after references were migrated to `Organizations`
- Commercial accounts with linked opportunities remain under `Accounts/`
- Opportunities were normalized to a stricter flat v4.1 shape
- `docs/schema-spec.md` is the only schema source in `docs/`
- Old docs were moved into `docs/archive/`

Still expect:
- older frontmatter in some records
- generated files in `crm-data/staging/`
- telemetry fields written by intelligence scripts
- occasional need for compatibility handling in readers

## Relationship Model

The memory system is assembled from:
- `Organizations`
- `Accounts`
- `Contacts`
- `Opportunities`
- `Leads`
- `Deals`
- `Notes`
- `Activities`
- `Tasks`
- Workspace-derived telemetry

When active relationship work exists, new `Notes` and `Activities` should usually attach primarily to the `Opportunity`.

Preferred primary-parent precedence:
1. `Opportunity`
2. `Contact`
3. `Account`

## Operational Loop

The normal operator loop is:

1. Sync Workspace
2. Review staged proposals and discoveries
3. Process Inbox items
4. Create or update durable records
5. Refresh dashboard and derived views

Derived outputs:
- `crm-data/DASHBOARD.md`
- `crm-data/INTELLIGENCE.md`
- `crm-data/RELATIONSHIP_MEMORY.md`
- `crm-data/staging/matches.json`

The home view is relationship-first, not timeline-first.

## Workspace Sync Rules

Workspace sync currently covers Gmail and Calendar.

Critical rules:
- always read Gmail body content or Calendar event details before creating an `Activity`
- use `source-ref` for dedupe
- persist checkpoint state in `crm-data/staging/workspace_sync_state.json`
- if `--since` is omitted, resume from checkpoint
- if `--since YYYY-MM-DD` is passed, treat that as an explicit backfill window

Important staging files:
- `crm-data/staging/workspace_updates.json`
- `crm-data/staging/discovery.json`
- `crm-data/staging/interactions.json`
- `crm-data/staging/workspace_sync_state.json`
- `crm-data/staging/matches.json`

## File Creation Rules

- Always use `templates/` for new records
- Use `YYYY-MM-DD` everywhere
- Quote wikilinks in frontmatter
- Preserve provenance fields when known
- Prefer structured frontmatter over body prose when the system depends on a field

Naming conventions:
- Activities: `YYYY-MM-DD-<slug>.md`
- Tasks: `YYYY-MM-DD-<slug>.md`
- Activities, Tasks, and Notes are stored under `YYYY/MM/` subfolders inside their entity directories.

## Git And Safety Rules

Be conservative.

- `crm-data` may be a nested repo, ignored directory, or ordinary subdirectory
- do not assume every write should be committed immediately
- do not use broad `git add .` in vault-related workflows unless explicitly intended
- avoid destructive mass rewrites unless the task clearly calls for them
- when changing schema-bearing data, prefer migration scripts plus validation over manual bulk edits

## Practical Rules For Agents

- Prefer empirical evidence from Workspace signals and linked records over assumption
- If an event already exists, enrich it rather than duplicating it
- If a staged Workspace proposal matches an existing Activity, attach the `source-ref` and remove the duplicate proposal
- Do not use `Notes` as raw scratch space
- Do not run `scripts/index-notes.py` unless explicitly instructed
- Improve consistency when touching a record, but do not silently rewrite unrelated data

## Important Scripts

### Core record creation and lifecycle
- `scripts/organization_manager.py`
- `scripts/lead_manager.py`
- `scripts/inbox_manager.py`
- `scripts/record_manager.py`

### Derived views and intelligence
- `.gemini/skills/update-dashboard/scripts/update-dashboard.py`
- `scripts/intelligence-engine.py`
- `scripts/relationship_memory.py`
- `scripts/matchmaker.py`

### Workspace sync
- `.gemini/skills/sync-workspace/scripts/sync-workspace.py`

### Recent migration helpers
- `scripts/migrate_accounts_to_organizations.py`
- `scripts/rewrite_organization_references.py`
- `scripts/migrate_opportunities_v41.py`

These migration scripts reflect real structural work already done. Use them as references for future migrations, not as permanent day-to-day entry points.

## Important Skills

Most relevant Gemini skills:
- `sync-workspace`
- `update-dashboard`
- `create-organization`
- `create-lead`
- `create-inbox-item`
- `create-note`
- `create-activity`
- `create-task`
- `matchmaker`
- `manage-intelligence`

Skill definitions live in `.gemini/skills/*/SKILL.md`.

## Examples And Docs

Current examples:
- `examples/`

Current canonical schema doc:
- `docs/schema-spec.md`

Archived historical docs:
- `docs/archive/`

Do not treat archived docs as authoritative if they conflict with the current schema spec or current code.

## If You Need To Be Productive Quickly

For a relationship-specific task:

1. Read the relevant `Organization`, `Account`, `Contact`, and `Opportunity`
2. Read recent linked `Activities`, `Notes`, and open `Tasks`
3. Check `DASHBOARD.md`, `RELATIONSHIP_MEMORY.md`, and `INTELLIGENCE.md`
4. If relevant, inspect `crm-data/staging/` for pending Workspace proposals
5. Make the smallest coherent change that improves record quality and execution clarity

For structural work:

1. Read `docs/schema-spec.md`
2. Inspect the relevant templates in `templates/`
3. Inspect the write path in the relevant script
4. Update readers for backward compatibility before removing old fields
5. Prefer additive migrations, validate, then remove deprecated structures later

## Current Sharp Edges

- `Deal-Flow/` is still the live deal directory
- some scripts still tolerate older aliases and compatibility fields
- telemetry fields are still persisted in some records
- some skill docs may lag the latest schema cleanup and should be updated when touched

## Bottom Line

Your job in this repo is to maintain a trustworthy relationship memory system.

That means:
- canonical new writes
- tolerant readers
- careful migrations
- evidence-based updates
- minimal duplication
- relationship-first outputs
