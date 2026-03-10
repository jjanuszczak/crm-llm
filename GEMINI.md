# Gemini Context: Personal CRM & Venture Brokerage (Logic)

## Project Overview
This directory (`/Users/johnjanuszczak/Projects/crm-logic`) contains the **Logic and Automation** for a Personal CRM system. The **CRM Data** (Accounts, Contacts, etc.) is stored in a separate directory specified in the `.env` file.

## Configuration
- **Environment:** A `.env` file in the root directory defines `CRM_DATA_PATH`.
- **Target Data:** The `crm-data` project follows the Obsidian Vault structure.
- **Tool Usage:** All file operations (read, write, list, search) for CRM entities (Accounts, Contacts, etc.) MUST be performed relative to the path specified in `CRM_DATA_PATH`. If a tool accepts a path, resolve it as `CRM_DATA_PATH + "/Relative/Path"`.

## Directory Structure (Logic)
- `.gemini/skills/`: Specialized instruction folders (Skills) defining agent automation.
- `Templates/`: Markdown templates used by skills to ensure consistent file structure.
- `scripts/`: Shared Python scripts for indexing and dashboarding.
- `.env`: Path to the active `crm-data` vault.

## Entity Schemas & Models (Data Context)
(These schemas apply to files found within `CRM_DATA_PATH`)

### 1. Accounts
... (rest of the schemas)
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
*   **YAML Frontmatter:**
    ```yaml
    full--name: "String"
    nickname: "String"
    account: "[[Link to Account]]"
    linkedin: "URL"
    email: "String"
    status: "qualified" | "lead" | "contacted"
    date-created: YYYY-MM-DD
    date-modified: YYYY-MM-DD
    ```

### 3. Opportunities
*   **YAML Frontmatter:**
    ```yaml
    opportunity-name: "[Account] - [Deal/Service] - [YYYY]"
    account: "[[Link to Account]]"
    deal: "[[Link to Deal-Flow]]" # If a brokerage match
    primary-contact: "[[Link to Contact]]"
    stage: discovery | proposal | negotiation | closed-won | closed-lost
    deal-value: Number (Expected Commission or Retainer Value)
    is-active: Boolean
    date-created: YYYY-MM-DD
    date-modified: YYYY-MM-DD
    ```

### 4. Deal-Flow (Startups)
*   **YAML Frontmatter:**
    ```yaml
    startup-name: "String"
    sector: "String"
    stage: "Seed" | "Series A" | etc.
    target-raise: Number (USD)
    valuation-cap: Number (USD)
    date-sourced: YYYY-MM-DD
    ```

### 5. Tasks
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
    ```

## Automated Workflows (Skills)

### Skill Structure
New skills must be created in `.gemini/skills/[skill_name]/` with:
*   `SKILL.md`: Core instructions.
*   `scripts/`: Automation scripts.
*   `reference/`: Supporting documents.

### Available Skills
*   `create_account`: Automates due diligence and file creation.
*   `create_contact`: Researches professional bios and engagement hooks.
*   `create_opportunity`: Initiates deal tracking.
*   `create_deal_flow`: Captures startup inventory and traction.
*   `create_activity`: Formats interaction logs and action items.
*   `create_task`: Manages actionable follow-ups and deadlines.
*   `update_dashboard`: Aggregates vault data into `DASHBOARD.md`.
*   `sync_workspace`: Proactively scans Gmail and Calendar for opportunity-linked updates.

## Operational Mandates & Hooks

### 1. The Startup Hook
Upon starting a new session or receiving the first command, the agent must:
1.  Run the `update_dashboard` skill to ensure the `DASHBOARD.md` is current.
2.  **Propose Workspace Sync:** Identify contacts linked to active opportunities and ask the user: *"I see [X] contacts in active opportunities. Should I scan Gmail and Calendar for updates since [Last Sync Date]?"*
3.  Proceed with `sync_workspace` only if the user confirms.

### 2. The State-Change Hook
Immediately after creating or modifying any entity file, the agent must update its `date-modified` field and run `update_dashboard`.

## Usage Guidelines
*   **Wikilinks:** Maintain deep interconnection. Link Contacts to Accounts and Tasks to Opportunities.
*   **Currency:** Retain original currency (e.g., PHP) but provide **USD conversions** (e.g., `₱20M (~$360k)`).
*   **Dates:** Always use `YYYY-MM-DD` format.
