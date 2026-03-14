# Gemini Context: Personal CRM & Venture Brokerage (Logic)

## Project Overview
This project contains the **Logic and Automation** for a personal agentic CRM system. The **CRM Data** (Accounts, Contacts, etc.) is stored in a **nested private git repository** located at the path specified in the `.env` file's `CRM_DATA_PATH`.

## Project Context & Business Logic
This system is optimized for a **Venture Brokerage and Strategic Advisory** model.

1.  **Deals (Inventory):** Located in `Deals/`. These are startups or projects seeking capital.
2.  **Accounts (Entities):** Located in `Accounts/`. These are **Clients**—entities that pay for services (Advisory, Consulting) or represent potential full-time roles.
3.  **Opportunities (Engagements):** Located in `Opportunities/`. These are the active "tickets" for revenue:
    *   **Brokerage:** Matching a **Deal** to an **Account** (Investor).
    *   **Direct Engagement:** An **Account** hiring you for a specific mandate.
    *   **Dual-Role:** A startup that is both a **Deal** (raising money) and an **Account** (paying for advisory).

## File Operations Protocol (CRITICAL)
1.  **Dynamic Path Resolution:** Always read `CRM_DATA_PATH` from `.env`.
2.  **Wikilink Property Standard:** All wikilinks in YAML frontmatter MUST be wrapped in double quotes: `account: "[[Name]]"`.
3.  **Automatic Bookkeeping:** After any write operation to `CRM_DATA_PATH`, you **MUST** commit the changes specifically within that subdirectory:
    `cd $CRM_DATA_PATH && git add . && git commit -m "agent: [action performed]"`
4.  **Template Mandate:** ALL new entity files MUST be based on the corresponding file in `templates/`.

## Entity Model (v4.0)

### 1. Inbox
*   `Inbox/` is the temporary raw capture queue.
*   Inbox items are processed into durable records and then deleted or marked processed.
*   Raw capture should not go straight into `Notes/` by default.

### 2. Notes
*   `Notes/` are first-class durable context records.
*   Notes use one `primary-parent` plus optional `secondary-links`.
*   Notes may exist without a paired `Activity` if they represent strategic context rather than a discrete event.

### 3. Activities
*   `Activities/` are first-class event records.
*   If a source item describes a real interaction, it should produce an `Activity`.
*   Activities follow the same parent-linking pattern as `Notes`.

### 4. Leads
*   `Leads/` are first-class pre-conversion records.
*   Supported statuses:
    *   `new`
    *   `prospect`
    *   `engaged`
    *   `qualified`
    *   `converted`
    *   `disqualified`
*   Default conversion path:
    *   `Lead -> Contact + Account + Opportunity`

### 5. Relationships
*   `Accounts/`, `Contacts/`, and `Opportunities/` remain the core durable relationship records.
*   Dashboarding and memory generation should treat relationship context as the combination of linked Notes, Activities, Tasks, Opportunities, and Workspace telemetry.

## Automated Workflows

### 1. The Dashboard Loop (`update-dashboard`)
Running `update-dashboard` triggers a sequential chain:
1.  **Relationship Assembly:** Scans Accounts, Contacts, Opportunities, Leads, Tasks, Activities, and Notes.
2.  **Dashboard Generation:** Refreshes `DASHBOARD.md` as a relationship-first home view.
3.  **Matchmaker:** Suggests Deal-Investor fits.
4.  **Intelligence Engine:** Refreshes relationship telemetry and `INTELLIGENCE.md`.
5.  **Relationship Memory:** Refreshes `RELATIONSHIP_MEMORY.md`.
6.  **Bookkeeping:** Commits generated outputs to the data repo unless explicitly skipped.

### 2. The Inbox Protocol
1.  **Ingestion:** User saves raw analysis/drafts in `CRM_DATA_PATH/Inbox/`.
2.  **Action:** Agent reads the Inbox item, executes the task, and processes it into durable records such as `Note`, `Activity`, `Task`, or `Lead`.
3.  **Cleanup:** The Inbox item is marked processed or deleted from the active queue once durable outputs are created.

### 3. Legacy Note Handling
Legacy `Notes/` files must be evaluated explicitly:
1.  If the file contains durable context, keep it as a `Note`.
2.  If it describes a real interaction, migrate it toward an `Activity` and optionally a supporting `Note`.
3.  If it was only temporary scratch capture, do not preserve the old “Notes as inbox” behavior. Prefer `Inbox/` for future raw intake.

### 4. Communication Mandate
- **Settings Resolution:** Always read `CRM_DATA_PATH/settings.json` for sender preferences.
- **Default Sender:** Use `preferred_email` for primary tasks.
- **Agent Identity:** Use `agent_email` (e.g. `leia@oakridgesadvisors.com`) for administrative or introductory tasks.

## Operational Mandates
- **No Reindexing:** DO NOT run `scripts/index-notes.py` unless explicitly instructed.
- **Precision:** Prioritize empirical evidence (Gmail/Calendar) over manual assumptions.
- **Formatting:** Use YYYY-MM-DD for all dates.
