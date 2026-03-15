# Gemini Context: CRM Logic

## What This Repo Is

This repo is the logic layer for a private AI-first personal CRM.

It is not the primary data store. The primary data store is the markdown/git vault at `CRM_DATA_PATH`.

Your job when operating in this repo is to help maintain a trustworthy relationship memory system for a single principal operator, optimized first for relationship-led advisory work.

## Operating Context

The system remains:
- personal, not multi-user
- markdown-native
- git-auditable
- AI-assisted
- relationship-first

The vault is intended to work with both autonomous and interactive agent behavior, but trust matters more than automation volume.

## Source Of Truth

Always resolve `CRM_DATA_PATH` dynamically from `.env` or the environment.

Typical local setup:

```text
CRM_DATA_PATH=./crm-data
```

Do not assume:
- the vault is checked into the main repo
- the vault uses only new schemas
- every record follows the latest template perfectly

## Product Goal

The north star is a trustworthy memory system that both the user and AI agents can rely on.

The system should help answer:
- who matters right now
- what happened recently
- what the current state of the relationship is
- what should happen next

## Current v4 Entity Model

### Inbox
- `Inbox/` is temporary raw capture.
- It replaces the old “notes as inbox” behavior.
- Inbox items should usually be processed into durable records, then deleted or marked processed.

### Notes
- `Notes/` are first-class durable context records.
- Notes are for background, interpretation, research, or strategic memory.
- Notes should usually link to a core record.
- Notes do not replace Activities when a real event happened.

### Activities
- `Activities/` are first-class event records.
- Use Activities for real interactions or events such as emails, meetings, calls, or significant analysis tied to a relationship.
- New Activities should use date-prefixed filenames.
- When ingesting Gmail or Calendar, always read the underlying content before writing the record.

### Leads
- `Leads/` are first-class pre-conversion records.
- Supported statuses:
  - `new`
  - `prospect`
  - `engaged`
  - `qualified`
  - `converted`
  - `disqualified`
- Leads may begin sparse.
- A `qualified` lead must have both person and company populated before conversion.
- Default conversion outcome is `Lead -> Contact + Account + Opportunity`.
- Converted leads should be archived rather than remain in the active set.

### Contacts
- Durable person records after direct creation or lead conversion.
- Contact should not carry the old pre-conversion meaning that now belongs on `Lead`.

### Accounts
- Durable organization records.
- Accounts represent clients, target organizations, partners, employers, or other relevant entities.

### Opportunities
- Concrete commercial or strategic engagements.
- These are the operational center of gravity when an active engagement exists.

### Deals
- Inventory seeking capital.
- Deals are distinct from Accounts and Opportunities, though they may be linked.

### Tasks
- Explicit next actions.
- New Tasks should use date-prefixed filenames.
- Tasks should stay linked to the relevant parent record and, when useful, a triggering Activity.

## Relationship Model

The memory system is assembled from linked records:
- `Accounts`
- `Contacts`
- `Opportunities`
- `Leads`
- `Notes`
- `Activities`
- `Tasks`
- Workspace-derived telemetry

When a relationship has an active `Opportunity`, that `Opportunity` should usually be the primary parent for new Notes and Activities.

Preferred primary-parent precedence:
1. `Opportunity`
2. `Contact`
3. `Account`

## Workspace Sync Rules

Workspace sync currently covers Gmail and Calendar.

Critical behavior:
- it stages or creates Activities from Workspace signals
- it must read Gmail body content or Calendar event details before creating a meaningful Activity
- it deduplicates using `source-ref`
- it persists the latest successful Gmail and Calendar checkpoints in `crm-data/staging/workspace_sync_state.json`
- if `--since` is omitted, it resumes from the saved checkpoint
- if `--since YYYY-MM-DD` is provided, that explicit backfill window overrides the saved checkpoint

Related files:
- `crm-data/staging/workspace_updates.json`
- `crm-data/staging/discovery.json`
- `crm-data/staging/interactions.json`
- `crm-data/staging/workspace_sync_state.json`

## Dashboard Loop

The main operational loop is:
1. sync Workspace
2. review staged proposals and discoveries
3. process Inbox items
4. create/update durable records
5. rerun the dashboard

`update-dashboard` refreshes:
- `DASHBOARD.md`
- matchmaker output
- `INTELLIGENCE.md`
- `RELATIONSHIP_MEMORY.md`

The home view is relationship-first, not timeline-first.

## File And Schema Rules

- Always use templates in `templates/` when creating new records.
- All wikilinks in YAML frontmatter must be quoted.
  - Example: `account: "[[Example Account]]"`
- Use `YYYY-MM-DD` date format everywhere.
- Prefer structured frontmatter fields when the system depends on them.
- Preserve provenance fields such as `source` and `source-ref` whenever possible.

## Naming Rules

Current expected conventions:
- new `Activities`: `YYYY-MM-DD-<slug>.md`
- new generated `Tasks`: `YYYY-MM-DD-<slug>.md`

Do not assume all existing vault files already follow this convention.

## Git And Bookkeeping

Be careful here.

Historically, some workflows committed inside the vault automatically, but current behavior is mixed. Do not assume every write should immediately commit.

Before using git:
- check whether `crm-data` is a nested repo, ignored directory, or ordinary subdirectory
- avoid broad `git add .` behavior in vault-related scripts unless that scope is explicitly intended

## What To Read First In A Live Vault

If you need to orient quickly, read:
1. `crm-data/DASHBOARD.md`
2. `crm-data/RELATIONSHIP_MEMORY.md`
3. `crm-data/INTELLIGENCE.md`
4. the relevant `Opportunity`, `Account`, and `Contact` files for the relationship you are working on

## Practical Rules For Agents

- Prefer empirical evidence from Gmail, Calendar, and linked records over assumptions.
- If a meeting or email was already captured manually, prefer enriching or linking the existing record over creating a duplicate.
- If a staged Workspace proposal is clearly the same event as an existing Activity, remove the proposal and attach the `source-ref` to the existing Activity.
- Do not use `Notes` as scratch space for raw intake.
- Do not run `scripts/index-notes.py` unless explicitly instructed.
- When in doubt, keep the active relationship set clean and archive obsolete pre-conversion records.

## Useful Entry Points

Important scripts:
- `scripts/lead_manager.py`
- `scripts/inbox_manager.py`
- `scripts/record_manager.py`
- `scripts/intelligence-engine.py`
- `scripts/relationship_memory.py`
- `scripts/matchmaker.py`
- `.gemini/skills/sync-workspace/scripts/sync-workspace.py`
- `.gemini/skills/update-dashboard/scripts/update-dashboard.py`

Important docs:
- `docs/prd-v4-memory-system.md`
- `docs/implementation-plan-v4-memory-system.md`
- `docs/schema-addendum-v4-core-records.md`
- `docs/schema-addendum-v4-existing-entities.md`
- `docs/schema-addendum-v4-deal-entity.md`
- `docs/legacy-notes-migration-v4.md`

Important skills:
- `sync-workspace`
- `update-dashboard`
- `create-lead`
- `create-inbox-item`
- `create-note`
- `create-activity`
- `create-task`
- `matchmaker`
- `manage-intelligence`

## Current Reality

This repo is usable now, but not perfectly uniform.

Expect:
- a mix of v4-native and older records in the vault
- some legacy frontmatter shapes still present
- some staged data under `crm-data/staging/`
- occasional need to normalize or dedupe older records by hand

Act accordingly: preserve working data, improve consistency when you touch a record, and avoid mass rewrites unless the task explicitly calls for them.
