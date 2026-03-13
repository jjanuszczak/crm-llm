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

## Entity Schemas (v3.0)

### 1. Accounts & Deal-Flow
*   **YAML Frontmatter:**
    ```yaml
    company-name: "String"
    warmth-score: 0-100 (managed by engine)
    warmth-status: "warm" | "neutral" | "cold"
    velocity-score: Number (interactions in last 7 days)
    account-warmth-index: 0-100 (aggregated from contacts)
    last-contacted: YYYY-MM-DD
    date-modified: YYYY-MM-DD
    ```

### 2. Contacts
*   **YAML Frontmatter:**
    ```yaml
    full-name: "String"
    account: "[[Link to Account]]" # If a Client
    deal: "[[Link to Deal]]"       # If a Startup/Inventory
    email: "String"
    status: "qualified" | "lead" | "contacted"
    warmth-score: 0-100
    velocity-score: 0-100
    ```

## Automated Workflows

### 1. The Intelligence Loop (`update-dashboard`)
Running `update-dashboard` triggers a sequential chain:
1.  **Index Notes:** Identifies all entities.
2.  **Matchmaker:** Suggests Deal-Investor fits.
3.  **Intelligence Engine:** Calculates warmth/velocity from `staging/interactions.json` and `Activities/`.
4.  **Dashboard Generation:** Refreshes `DASHBOARD.md` and `INTELLIGENCE.md`.
5.  **Bookkeeping:** Commits all telemetry and file updates to the data repo.

### 2. The Notes Inbox Protocol
1.  **Ingestion:** User saves raw analysis/drafts in `CRM_DATA_PATH/Notes/`.
2.  **Action:** Agent reads the note, executes the task (e.g. sends email), and converts the note into a formal `Activity`.
3.  **Cleanup:** Original note is moved to `CRM_DATA_PATH/.trash/`.

### 3. Communication Mandate
- **Settings Resolution:** Always read `CRM_DATA_PATH/settings.json` for sender preferences.
- **Default Sender:** Use `preferred_email` for primary tasks.
- **Agent Identity:** Use `agent_email` (e.g. `leia@oakridgesadvisors.com`) for administrative or introductory tasks.

## Operational Mandates
- **No Reindexing:** DO NOT run `scripts/index-notes.py` unless explicitly instructed.
- **Precision:** Prioritize empirical evidence (Gmail/Calendar) over manual assumptions.
- **Formatting:** Use YYYY-MM-DD for all dates.
