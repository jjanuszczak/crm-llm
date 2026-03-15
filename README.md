# CRM Logic

This repo contains the logic, templates, scripts, and skill instructions for a private AI-first personal CRM built on a markdown/git vault.

The system is optimized for relationship-led advisory work, while still supporting consulting, dealmaking, and founder/investor matchmaking workflows.

The source of truth is not this repo. The source of truth is the private vault at `CRM_DATA_PATH`, typically `./crm-data/`.

## What This Repo Does

This repo gives an agent or developer the machinery to:
- create and maintain CRM records in markdown
- sync Gmail and Google Calendar into relationship memory
- generate a relationship-first dashboard
- track leads before conversion
- process raw capture through an `Inbox/`
- assemble relationship memory from `Notes`, `Activities`, `Tasks`, and linked entities
- suggest investor/deal matches

## Mental Model

Think in two layers:
- `crm-logic/`: public-friendly logic layer
- `crm-data/`: private vault and operational system of record

The vault is where the real work happens. The logic layer exists to read, write, enrich, and synthesize that vault.

## Current v4 Model

The system is now a v4 memory system. The key record types are:
- `Inbox`: temporary raw capture
- `Lead`: pre-conversion relationship record
- `Contact`: person record
- `Account`: company/entity record
- `Opportunity`: active engagement or commercial path
- `Deal`: startup/inventory seeking capital
- `Note`: durable context and strategic memory
- `Activity`: real interaction or event
- `Task`: explicit next action

Important v4 rules:
- `Inbox/` replaces the old “notes as inbox” pattern.
- `Notes/` are durable context, not raw intake.
- If something happened, it should usually create an `Activity`.
- `Lead` is first-class and converts by default to `Contact + Account + Opportunity`.
- The default home view is relationship-first, not chronology-first.

## Quick Start

### Prerequisites

- Python 3
- Gemini CLI
- `gws` CLI authenticated to the relevant Google Workspace account

### Configure the vault path

Create `.env` in the repo root:

```text
CRM_DATA_PATH=./crm-data
```

### Initialize a fresh vault

```bash
python3 .gemini/skills/init-crm-data/scripts/init-vault.py crm-data
```

### Most useful commands

Sync Workspace:

```bash
CRM_DATA_PATH=./crm-data python3 .gemini/skills/sync-workspace/scripts/sync-workspace.py
```

Refresh dashboard and derived views:

```bash
CRM_DATA_PATH=./crm-data python3 .gemini/skills/update-dashboard/scripts/update-dashboard.py --skip-followups --skip-commit
```

Create a lead:

```bash
python3 scripts/lead_manager.py create --name "Example Lead" --status new
```

Process an Inbox item:

```bash
python3 scripts/inbox_manager.py process <item> --outputs note activity task --primary-parent-type opportunity --primary-parent "Opportunities/Example"
```

Create an Activity directly:

```bash
python3 scripts/record_manager.py create-activity --title "Intro call with Jane" --activity-type meeting --date 2026-03-15 --primary-parent-type opportunity --primary-parent "Opportunities/Example"
```

## Day-To-Day Operating Loop

For a new operator or agent, the normal loop is:

1. Run Workspace sync.
2. Review `crm-data/staging/workspace_updates.json`.
3. Review `crm-data/staging/discovery.json`.
4. Process or create `Inbox/` items into durable records.
5. Create or update `Leads`, `Activities`, `Notes`, and `Tasks` as needed.
6. Run the dashboard refresh.

If you only do one thing to get oriented in a live vault, read:
- `crm-data/DASHBOARD.md`
- `crm-data/INTELLIGENCE.md`
- `crm-data/RELATIONSHIP_MEMORY.md`

## Workspace Sync Behavior

Workspace sync now has two important guarantees:
- it always tries to read the underlying Gmail body or Calendar event details before creating a durable Activity
- it persists a sync checkpoint in `crm-data/staging/workspace_sync_state.json`

That means:
- repeated sync runs resume from the last successful Gmail/Calendar checkpoint by default
- `source-ref` is still used as a second dedupe layer
- passing `--since YYYY-MM-DD` overrides the saved checkpoint for backfills

## Naming Conventions

Use `YYYY-MM-DD` dates everywhere.

Current filename conventions:
- new `Activities`: `YYYY-MM-DD-<slug>.md`
- new generated `Tasks`: `YYYY-MM-DD-<slug>.md`

Legacy files may still exist in older filename shapes. Do not assume the whole vault is perfectly migrated.

## Important Operational Rules

- Always resolve `CRM_DATA_PATH` dynamically from `.env` or the environment.
- Always use the templates in `templates/` for new records.
- All wikilinks in YAML frontmatter must be quoted, for example:
  - `account: "[[Example Account]]"`
- Prefer updating existing linked records over creating duplicates.
- For Gmail and Calendar ingestion, do not create meaningful records from subject lines alone.
- `crm-data` may be a nested git repo or ignored locally. Check before assuming normal git behavior.

## Key Skills

The most relevant skills for real use are:
- `sync-workspace`
- `update-dashboard`
- `create-lead`
- `create-inbox-item`
- `create-note`
- `create-activity`
- `create-task`
- `matchmaker`
- `manage-intelligence`

Skill definitions live in `.gemini/skills/*/SKILL.md`.

## Important Scripts

- [sync-workspace.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/sync-workspace/scripts/sync-workspace.py#L1): Gmail/Calendar ingestion
- [update-dashboard.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/update-dashboard/scripts/update-dashboard.py#L1): dashboard refresh and downstream generation
- [lead_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/lead_manager.py#L1): lead lifecycle and conversion
- [inbox_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/inbox_manager.py#L1): Inbox creation and processing
- [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py#L1): first-class Note and Activity creation
- [relationship_memory.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/relationship_memory.py#L1): relationship memory assembly
- [intelligence-engine.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/intelligence-engine.py#L1): telemetry and intelligence generation
- [matchmaker.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/matchmaker.py#L1): deal/account matching

## Recommended Reading

For product and schema context, read:
- [prd-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/prd-v4-memory-system.md#L1)
- [implementation-plan-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/implementation-plan-v4-memory-system.md#L1)
- [schema-addendum-v4-core-records.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-addendum-v4-core-records.md#L1)
- [schema-addendum-v4-existing-entities.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-addendum-v4-existing-entities.md#L1)
- [schema-addendum-v4-deal-entity.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-addendum-v4-deal-entity.md#L1)
- [legacy-notes-migration-v4.md](/Users/johnjanuszczak/Projects/crm-logic/docs/legacy-notes-migration-v4.md#L1)

## Current Rough Edges

Be aware of these realities:
- the vault contains a mix of v4-native and older records
- some legacy Activities and Tasks still use older frontmatter shapes
- not every workflow auto-commits vault changes
- GitHub MCP auth may be unreliable in this environment; `gh` CLI may be the fallback

If you are new to the project, start with the dashboard, inspect one relationship end to end, then run Workspace sync and review staged proposals before making broader changes.
