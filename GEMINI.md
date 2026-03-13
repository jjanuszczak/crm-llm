# Gemini Context: Personal CRM & Venture Brokerage (Logic)

## Project Overview
This project contains the **Logic and Automation** for a personal agentic CRM system. The **CRM Data** (Accounts, Contacts, etc.) is stored in a **nested git repository** located at the path specified in the `.env` file's `CRM_DATA_PATH` variable.

## Project Context & Business Logic
This system is optimized for a **Venture Brokerage and Strategic Advisory** model. It tracks three primary pillars:

1.  **Deals (Inventory):** Located in `Deals/`. These are startups or projects seeking capital (equity/debt).
2.  **Accounts (Entities):** Located in `Accounts/`. These are **Clients**—entities that pay for services (Advisory, Consulting, Retainers) or represent potential full-time roles.
3.  **Opportunities (Engagements):** Located in `Opportunities/`. These are the active "tickets" for revenue:
    *   **Brokerage:** Matching a **Deal** to an **Account** (Investor).
    *   **Direct Engagement:** An **Account** hiring you for a specific mandate (Advisory, Board Seat, CEO Role).
    *   **Dual-Role:** A startup that is both a **Deal** (raising money) and an **Account** (paying you for advisory/fundraising support).

## Configuration & Environment
- **Strategy:** Dynamic Nested Repo (The logic remains constant, while the target data repository can be swapped or renamed via `.env`).
- **Environment:** A `.env` file in the root directory MUST define `CRM_DATA_PATH`.
- **Constraint:** `CRM_DATA_PATH` **MUST** point to a subdirectory **within** the current project root (e.g., `./crm-data`).
- **Tool Requirements:**
    *   **GWS CLI:** Must be installed and authenticated for `sync-google-tasks`.
    *   **Python 3:** Required for dashboarding and synchronization scripts.

## File Operations Protocol (CRITICAL)
1. **Dynamic Path Resolution:** Always read the current `CRM_DATA_PATH` from `.env`.
2. **Native Tools:** Use `read_file`, `write_file`, and `replace` directly on files within the resolved `CRM_DATA_PATH` tree.
3. **Template Mandate:** ALL new entity files MUST be based on the corresponding file in the `templates/` directory to ensure schema consistency.
4. **Automatic Bookkeeping:** After any write operation to `CRM_DATA_PATH`, you **MUST** commit the changes specifically within that subdirectory:
   ```bash
   cd $CRM_DATA_PATH && git add . && git commit -m "agent: [action performed]"
   ```
5. **Isolation:** The directory specified in `CRM_DATA_PATH` must be ignored by the main `crm-logic` repository's `.gitignore`.

## Directory Structure (Logic)
- `.gemini/skills/`: Specialized instruction folders (Skills) defining agent automation.
- `templates/`: Markdown templates used by skills to ensure consistent file structure.
- `scripts/`: Shared Python scripts for indexing and dashboarding.
- `.env`: Path to the active CRM data vault.

## Entity Schemas & Models (Data Context)
(These schemas apply to files found within `CRM_DATA_PATH`)

### 1. Accounts
*   **Location:** `CRM_DATA_PATH/Accounts/`
*   **YAML Frontmatter:**
    ```yaml
    company-name: "String"
    type: "investor" | "corporate" | "startup"
    headquarters: "String"
    industry: "String"
    priority: "high" | "medium" | "low"
    stage: "prospect" | "engaged" | "customer" | "churned"
    investment-mandate: ["Sectors"]
    check-size: "String"
    date-created: YYYY-MM-DD
    date-modified: YYYY-MM-DD
    ```

### 2. Contacts
*   **Location:** `CRM_DATA_PATH/Contacts/`
*   **YAML Frontmatter:**
    ```yaml
    full-name: "String"
    nickname: "String"
    account: "[[Link to Account]]"
    linkedin: "URL"
    email: "String"
    status: "qualified" | "lead" | "contacted"
    date-created: YYYY-MM-DD
    date-modified: YYYY-MM-DD
    ```

### 3. Opportunities
*   **Location:** `CRM_DATA_PATH/Opportunities/`
*   **YAML Frontmatter:**
    ```yaml
    opportunity-name: "[Account] - [Deal/Service] - [YYYY]"
    account: "[[Link to Account]]"
    deal: "[[Link to Deal-Flow]]" # Optional: Only if a brokerage match
    primary-contact: "[[Link to Contact]]"
    stage: discovery | proposal | negotiation | closed-won | closed-lost
    deal-value: Number (Expected Commission or Retainer Value)
    is-active: Boolean
    date-created: YYYY-MM-DD
    date-modified: YYYY-MM-DD
    ```

### 4. Deal-Flow (Startups)
*   **Location:** `CRM_DATA_PATH/Deals/`
*   **YAML Frontmatter:**
    ```yaml
    startup-name: "String"
    sector: "String"
    stage: "Seed" | "Series A" | etc.
    target-raise: Number (USD)
    valuation-cap: Number (USD)
    pitch-deck-url: "URL"
    google-drive-url: "URL"
    date-sourced: YYYY-MM-DD
    date-modified: YYYY-MM-DD
    ```

### 5. Tasks
*   **Location:** `CRM_DATA_PATH/Tasks/`
*   **YAML Frontmatter:**
    ```yaml
    task-name: "String"
    status: "todo" | "in-progress" | "waiting" | "completed"
    priority: "high" | "medium" | "low"
    due-date: YYYY-MM-DD
    account: "[[Link]]"
    contact: "[[Link]]"
    opportunity: "[[Link]]"
    type: "call" | "email" | "prep" | "follow-up"
    email-link: "URL"
    meeting-notes: "URL"
    ```

### 6. Activities
*   **Location:** `CRM_DATA_PATH/Activities/`
*   **YAML Frontmatter:**
    ```yaml
    activity-date: YYYY-MM-DD
    type: "call" | "email" | "meeting" | "analysis" | "note"
    contacts: ["[[Link]]"]
    opportunity: "[[Link]]"
    email-link: "URL"
    meeting-notes: "URL"
    ```

### 7. Reports
*   **Location:** `CRM_DATA_PATH/Reports/`
*   **Schema:** Defined in `templates/report-template.md`. Stores daily progress reports.

## Automated Workflows (Skills)

### Available Skills
*   `create-account`: Automates due diligence and file creation.
*   `create-contact`: Researches professional bios and engagement hooks.
*   `create-opportunity`: Initiates deal tracking.
*   `create-deal`: Captures startup inventory and traction.
*   `create-activity`: Formats interaction logs and action items.
*   `create-task`: Manages actionable follow-ups and deadlines.
*   `update-dashboard`: Aggregates vault data into `DASHBOARD.md`.
*   `sync-workspace`: Proactively scans Gmail and Calendar for opportunity-linked updates.
*   `sync-google-tasks`: Bidirectional sync between local CRM and Google Tasks using GWS CLI.
*   `init-crm-data`: Initializes a new nested data repository with standard folders and git config.
*   `create-daily-report`: Synthesizes session actions into a structured report saved in `Reports/`.

### The Notes Inbox Protocol
1.  **Ingestion:** User saves raw analysis, drafts, or snippets in `CRM_DATA_PATH/Notes/`.
2.  **Trigger:** User instructs: "Process note [X] to [Send Email/Update Deal]."
3.  **Action:** Agent reads the note, executes the requested task (e.g., drafts email), and then converts the note into a formal `Activity`.
4.  **Conversion:** The original file is moved to `CRM_DATA_PATH/Activities/` with a new name (e.g., `YYYY-MM-DD - analysis - [Subject].md`) and appropriate YAML frontmatter.
5.  **Linking:** Agent ensures the new Activity is wikilinked to the relevant [[Account]] or [[Contact]].
6.  **Cleanup:** If the user prefers, the original file in `Notes/` can be moved to `CRM_DATA_PATH/.trash/` after conversion.

## Operational Mandates & Hooks

### 0. Suppression Notice (TEMPORARY)
- **DO NOT run `scripts/index-notes.py`** or trigger any reindexing process until explicitly instructed by the user. This takes precedence over all other instructions.

### 1. The Startup Hook
Upon starting a new session or receiving the first command, the agent must:
1.  Read `CRM_DATA_PATH` from `.env`.
2.  Verify `gws` CLI status if a task sync is requested.
3.  Run the `update-dashboard` skill to ensure the `DASHBOARD.md` is current.
4.  **Propose Workspace Sync:** Identify contacts linked to active opportunities and ask the user: *"I see [X] contacts in active opportunities. Should I scan Gmail and Calendar for updates since [Last Sync Date]?"*
5.  Proceed with `sync-workspace` only if the user confirms.

### 2. The State-Change Hook (Automatic Bookkeeping)
Immediately after creating or modifying any entity file:
1. Update its `date-modified` field.
2. Commit the change: `cd $CRM_DATA_PATH && git add . && git commit -m "agent: [action performed]"`
3. Run `update-dashboard`.

### 3. Communication Mandate (CRITICAL)
- **Settings Resolution:** Before any Gmail or communication operation, the agent MUST read `CRM_DATA_PATH/settings.json` to resolve the current user preferences.
- **Default Sender:** ALWAYS use the `preferred_email` found in settings for all primary Gmail operations unless otherwise specified.
- **Agent Identity:** The `agent_email` in settings should be used if the user requests an action to be sent "from the agent" or for automated status updates.

## Usage Guidelines
*   **Wikilinks:** Maintain deep interconnection. Link Contacts to Accounts and Tasks to Opportunities.
*   **Wikilink Property Standard (CRITICAL):** All wikilinks stored in YAML frontmatter MUST be wrapped in double quotes. This is mandatory for the links to be functional in Obsidian.
    *   **Correct:** `account: "[[Account Name]]"`
    *   **Correct:** `deal: "[[Deal Name]]"`
    *   **Incorrect:** `account: [[Account Name]]` (The brackets alone cause parsing failure in YAML)
*   **Currency:** Retain original currency (e.g., PHP) but provide **USD conversions** (e.g., `₱20M (~$360k)`).
*   **Dates:** Always use `YYYY-MM-DD` format.
