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

## Start Here Fast

If you are a new agent or developer and need to get productive quickly, read in this order:

1. `docs/schema-spec.md`
2. `AGENTS.md`
3. `crm-data/DASHBOARD.md`
4. `crm-data/index.md`
5. `crm-data/log.md`

Then adopt these current assumptions:
- `crm-data/` is the system of record
- `crm-daily-processing` is the preferred top-level daily workflow
- `Deal-Flow/` is still the live deal inventory directory
- `waiting` is a first-class task state and its `due-date` should usually mean the next review/check-back date
- a company may exist both as a `Deal` and as an `Opportunity`, but those records mean different things

Use this distinction:
- `Deal`: a company / startup in inventory that can be matched to investors
- `Opportunity`: a potential paid mandate, advisory engagement, or other commercial path for John

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

## Current Model

The system currently uses this memory model. The key record types are:
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

Important current rules:
- `Inbox/` replaces the old “notes as inbox” pattern.
- `Notes/` are durable context, not raw intake.
- If something happened, it should usually create an `Activity`.
- `Lead` is first-class and converts by default to `Organization + Contact + Account + Opportunity`.
- `Organization` owns stable identity/classification, while `Account` owns the active commercial relationship.
- Investor mandate and check-size stay on the organization side; fundraising stage and target raise stay on `Deal`.
- `commercial-value` is canonical on Opportunities; `deal-value` is compatibility-only.
- The default home view is relationship-first, not chronology-first.
- `Deal` and `Opportunity` are intentionally separate:
  - use `Deal` for investor-shop inventory
  - use `Opportunity` for John's possible or active mandate with that company

## Quick Start

### Prerequisites

- Python 3
- Gemini CLI or another compatible coding agent runner
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
CRM_DATA_PATH=./crm-data python3 .gemini/skills/crm-ingest-gws/scripts/ingest.py
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

Create an Account linked to an Organization:

```bash
python3 scripts/account_manager.py create --organization "Organizations/Example-Capital" --relationship-stage prospect --strategic-importance medium
```

Create a Contact linked to an Account:

```bash
python3 scripts/contact_manager.py create --name "Jane Doe" --account "Accounts/Example-Capital" --email "jane@example.com"
```

Create a Deal in the live `Deal-Flow/` inventory:

```bash
python3 scripts/deal_manager.py create --name "Example Startup" --fundraising-stage "Series A" --coverage-status active
```

Create or update a Task with the live status model:

```bash
python3 scripts/task_manager.py create --name "Follow up with Jane" --due-date 2026-04-10 --primary-parent-type opportunity --primary-parent "Opportunities/Example"
python3 scripts/task_manager.py set-status "Tasks/2026/04/2026-04-10-follow-up-with-jane.md" --status waiting --review-date 2026-04-13
python3 scripts/task_manager.py set-status "Tasks/2026/04/2026-04-10-follow-up-with-jane.md" --status completed
```

## Day-To-Day Operating Loop

For a new operator or agent, the normal loop is now best treated as the top-level skill `crm-daily-processing`.

That workflow should:
- run Workspace ingest
- review staged suggestions
- ask the user for off-system updates from WhatsApp, in-person meetings, calls, and other uncaptured channels
- reconcile `todo`, `waiting`, and stale tasks
- review live opportunities and leads
- refresh the dashboard and derived views

At a lower level, the manual sequence is:

1. Run Workspace sync.
2. Review `crm-data/staging/activity_updates.json`.
3. Review `crm-data/staging/contact_discoveries.json` and `crm-data/staging/lead_decisions.json`.
4. Review `crm-data/staging/opportunity_suggestions.json` and `crm-data/staging/task_suggestions.json`.
5. Process or create `Inbox/` items into durable records.
6. Create or update `Leads`, `Activities`, `Notes`, and `Tasks` as needed.
7. Run the dashboard refresh.

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

Current execution rules:
- `todo`: you owe the next move
- `waiting`: someone else owes the next move
- `completed`: done or clearly superseded
- when moving a task to `waiting`, update `due-date` to the next review date
- for company fundraising work, decide explicitly whether you are recording a `Deal`, an `Opportunity`, or both

Preferred current write surface:
- use the manager CLIs for `Organization`, `Account`, `Contact`, `Deal`, `Task`, `Lead`, and `Opportunity` lifecycle work
- use `record_manager.py` for first-class `Activity` and `Note` creation
- use `inbox_manager.py` for raw capture processing

## Key Skills

The most relevant skills for real use are:
- `crm-daily-processing`
- `crm-ingest-gws`
- `update-dashboard`
- `crm-lead-manager`
- `crm-opportunity-manager`
- `crm-create-account`
- `crm-create-contact`
- `crm-create-deal`
- `crm-create-daily-report`
- `crm-create-organization`
- `crm-create-lead`
- `crm-create-inbox-item`
- `crm-create-note`
- `crm-create-activity`
- `crm-create-task`
- `matchmaker`
- `manage-intelligence`

Skill definitions live in `.gemini/skills/*/SKILL.md`.

## Important Scripts

- [ingest.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-ingest-gws/scripts/ingest.py#L1): Gmail/Calendar ingestion and staged CRM decisioning
- [update-dashboard.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/update-dashboard/scripts/update-dashboard.py#L1): dashboard refresh and downstream generation
- [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py#L1): organization creation
- [account_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/account_manager.py#L1): account creation and update
- [contact_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/contact_manager.py#L1): contact creation and update
- [deal_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/deal_manager.py#L1): deal inventory creation and update
- [lead_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/scripts/lead_manager.py#L1): lead lifecycle and conversion
- [opportunity_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-opportunity-manager/scripts/opportunity_manager.py#L1): opportunity lifecycle and execution workflows
- [task_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/task_manager.py#L1): task creation, update, and status management
- [inbox_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/inbox_manager.py#L1): Inbox creation and processing
- [navigation_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/navigation_manager.py#L1): vault root `index.md` generation and `log.md` appends
- [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py#L1): first-class Note and Activity creation
- [relationship_memory.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/relationship_memory.py#L1): relationship memory assembly
- [intelligence-engine.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/intelligence-engine.py#L1): telemetry and intelligence generation
- [matchmaker.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/matchmaker.py#L1): deal/account matching
- [migrate_accounts_to_organizations.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/migrate_accounts_to_organizations.py#L1): reference migration helper
- [rewrite_organization_references.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/rewrite_organization_references.py#L1): reference rewrite helper
- [migrate_opportunities_v41.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/migrate_opportunities_v41.py#L1): opportunity schema migration helper

## Recommended Reading

For current product and schema context, read:
- [schema-spec.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-spec.md#L1)
- [AGENTS.md](/Users/johnjanuszczak/Projects/crm-logic/AGENTS.md#L1)
- [README.md](/Users/johnjanuszczak/Projects/crm-logic/README.md#L1)
- [examples/README.md](/Users/johnjanuszczak/Projects/crm-logic/examples/README.md#L1)

Historical and superseded design docs live in:
- [archive](/Users/johnjanuszczak/Projects/crm-logic/docs/archive)

## Current Rough Edges

Be aware of these realities:
- the vault contains a mix of current-shape and older records
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
