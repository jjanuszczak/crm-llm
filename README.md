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

The current canonical schema lives in `docs/schema-spec.md`.

## Mental Model

Think in two layers:
- `crm-logic/`: public-friendly logic layer
- `crm-data/`: private vault and operational system of record

The vault is where the real work happens. The logic layer exists to read, write, enrich, and synthesize that vault.

## Navigation Artifacts

The vault root now maintains two navigation files for agents and operators:
- `index.md`: a generated, content-oriented catalog of every CRM record grouped by entity type
- `log.md`: an append-only chronological ledger of mutation workflows such as creates, conversions, inbox processing, and ingest runs

Operating rules:
- read `index.md` first when locating relevant CRM pages
- treat `index.md` as derived state and rebuildable
- treat `log.md` as append-only operational history
- mutation workflows should update both automatically

## Current v4 Model

The system is now a v4 memory system. The key record types are:
- `Organization`: stable market entity
- `Inbox`: temporary raw capture
- `Lead`: pre-conversion relationship record
- `Contact`: person record
- `Account`: commercial relationship record
- `Opportunity`: active engagement or commercial path
- `Deal`: startup/inventory seeking capital
- `Note`: durable context and strategic memory
- `Activity`: real interaction or event
- `Task`: explicit next action

Important v4 rules:
- `Inbox/` replaces the old “notes as inbox” pattern.
- `Notes/` are durable context, not raw intake.
- If something happened, it should usually create an `Activity`.
- `Lead` is first-class and converts by default to `Organization + Contact + Account + Opportunity`.
- `Organization` owns stable identity/classification, while `Account` owns the active commercial relationship.
- Investor mandate and check-size stay on the organization side; fundraising stage and target raise stay on `Deal`.
- `commercial-value` is canonical on Opportunities; `deal-value` is compatibility-only.
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
python3 .gemini/skills/crm-lead-manager/scripts/lead_manager.py create --name "Example Lead" --status new
```

Process an Inbox item:

```bash
python3 scripts/inbox_manager.py process <item> --outputs note activity task --primary-parent-type opportunity --primary-parent "Opportunities/Example"
```

Create an Activity directly:

```bash
python3 scripts/record_manager.py create-activity --title "Intro call with Jane" --activity-type meeting --date 2026-03-15 --primary-parent-type opportunity --primary-parent "Opportunities/Example"
```

Create or review an Opportunity workflow:

```bash
python3 scripts/opportunity_manager.py review "Opportunities/Example"
```

Rebuild the CRM index manually:

```bash
python3 scripts/navigation_manager.py rebuild-index
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
- `crm-data/index.md`

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
- all CRM record filenames use hyphen-separated slugs; do not use spaces or punctuation in record filenames
- new `Activities`: `YYYY-MM-DD-<slug>.md`
- new generated `Tasks`: `YYYY-MM-DD-<slug>.md`
- `Activities/`, `Tasks/`, and `Notes/` are bucketed under `YYYY/MM/`

Legacy files may still exist in older filename shapes. Do not assume the whole vault is perfectly migrated.

## Important Operational Rules

- Always resolve `CRM_DATA_PATH` dynamically from `.env` or the environment.
- Always use the templates in `templates/` for new records.
- Treat `index.md` as generated state; rebuild it rather than editing it manually.
- Treat `log.md` as append-only; do not rewrite old entries.
- All wikilinks in YAML frontmatter must be quoted, for example:
  - `account: "[[Example Account]]"`
- Prefer updating existing linked records over creating duplicates.
- For Gmail and Calendar ingestion, do not create meaningful records from subject lines alone.
- `crm-data` may be a nested git repo or ignored locally. Check before assuming normal git behavior.

## Key Skills

The most relevant skills for real use are:
- `sync-workspace`
- `update-dashboard`
- `crm-lead-manager`
- `crm-opportunity-manager`
- `create-organization`
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
- [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py#L1): organization creation
- [lead_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/scripts/lead_manager.py#L1): lead lifecycle and conversion
- [opportunity_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-opportunity-manager/scripts/opportunity_manager.py#L1): opportunity lifecycle and execution workflows
- [inbox_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/inbox_manager.py#L1): Inbox creation and processing
- [navigation_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/navigation_manager.py#L1): vault root `index.md` generation and `log.md` appends
- [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py#L1): first-class Note and Activity creation
- [relationship_memory.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/relationship_memory.py#L1): relationship memory assembly
- [intelligence-engine.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/intelligence-engine.py#L1): telemetry and intelligence generation
- [matchmaker.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/matchmaker.py#L1): deal/account matching
- [migrate_accounts_to_organizations.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/migrate_accounts_to_organizations.py#L1): reference migration helper
- [rewrite_organization_references.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/rewrite_organization_references.py#L1): reference rewrite helper
- [migrate_opportunities_v41.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/migrate_opportunities_v41.py#L1): opportunity schema normalization helper

## Recommended Reading

For current product and schema context, read:
- [schema-spec.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-spec.md#L1)
- [GEMINI.md](/Users/johnjanuszczak/Projects/crm-logic/GEMINI.md#L1)
- [README.md](/Users/johnjanuszczak/Projects/crm-logic/README.md#L1)
- [examples/README.md](/Users/johnjanuszczak/Projects/crm-logic/examples/README.md#L1)

Historical and superseded design docs live in:
- [archive](/Users/johnjanuszczak/Projects/crm-logic/docs/archive)

## Current Rough Edges

Be aware of these realities:
- the vault contains a mix of v4-native and older records
- the vault still uses `Deal-Flow/` as the live deal directory
- some legacy Activities and Tasks still use older frontmatter shapes
- some compatibility fields are still tolerated by readers during migration cleanup
- not every workflow auto-commits vault changes
- GitHub MCP auth may be unreliable in this environment; `gh` CLI may be the fallback

If you are new to the project, start with the dashboard, inspect one relationship end to end, then run Workspace sync and review staged proposals before making broader changes.

## Agent Navigation Pattern

When working inside a live vault:
1. Read `index.md` at the vault root to find candidate records.
2. Drill into the linked pages you actually need.
3. Let mutation workflows append to `log.md`.
4. Use `log.md` to understand what changed recently and which workflows have already run.
