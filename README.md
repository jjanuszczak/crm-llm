# CRM Logic: Agentic Venture Brokerage & Personal CRM

This repository contains the **Logic and Automation** for a personal agentic CRM system. It is designed to work with the [Gemini CLI](https://github.com/google/gemini-cli) to automate due diligence, relationship intelligence, and brokerage matchmaking.

## 🏗 Architecture: The "Memory System"

This project follows a **decoupled architecture** built around a private markdown/git vault:
*   **Logic (This Repo):** Contains the skills, scripts, templates, and instructions for the agent. This is public-friendly.
*   **Data (Private Vault):** Your actual CRM data (Accounts, Contacts, etc.) is stored in a separate private Git repository (e.g., `crm-data/`). 
*   **Memory Layer:** Relationship memory is assembled from linked `Notes`, `Activities`, `Tasks`, `Leads`, `Opportunities`, and Google Workspace signals.

---

## 🚀 Getting Started

### 1. Prerequisites
*   **[Gemini CLI](https://github.com/google/gemini-cli)** installed and authenticated.
*   **[GWS CLI](https://github.com/googleworkspace/cli)** installed and authenticated.
*   **Python 3.x** for sync, relationship memory, and dashboard generation.

### 2. Configuration
Create a `.env` file in the root directory:
```text
CRM_DATA_PATH=./crm-data
```

### 3. Initialize your Data Vault
If starting from scratch, create a new private data repository:
```bash
python3 .gemini/skills/init-crm-data/scripts/init-vault.py crm-data
```

---

## 🛠 Available Skills

The agent can perform the following automated workflows:

| Skill | Command | Description |
| :--- | :--- | :--- |
| **Dashboard** | `update-dashboard` | Generates the relationship-first home view and refreshes downstream memory/intelligence views. |
| **Manage Intel** | `manage-intelligence`| Approve/Ignore discoveries and refresh intelligence outputs. |
| **Workspace Sync**| `sync-workspace` | Scans Gmail/Calendar for updates. Supports **Autonomous** and **Interactive** modes. |
| **Matchmaker** | `matchmaker` | Autonomously suggests matches between **Deals** (inventory) and **Accounts** (investors). |
| **Lead Flow** | `create-lead` | Creates and manages first-class leads before conversion into permanent CRM records. |
| **Inbox** | `create-inbox-item` | Creates and processes temporary Inbox captures into durable records. |
| **Notes** | `create-note` | Creates first-class durable notes linked to the relevant relationship record. |
| **Activities** | `create-activity` | Creates first-class activity records for real interactions or events. |
| **Account DD** | `create-account` | Researches a company and generates a comprehensive DD report. |
| **Contact Bio** | `create-contact` | Researches professional bios and engagement hooks. |
| **Deal Flow** | `create-deal` | Captures startup inventory and maps LinkedIn "Warm Paths". |
| **Tasks** | `create-task` | Manages follow-ups with automatic linking to Activities. |

---

## 📋 Core Concepts & Protocols

### Deals vs. Accounts
*   **Deal:** Inventory (startups/projects) seeking capital. Located in `Deals/`.
*   **Account:** Clients or Partners paying for services (Advisory, Consulting). Located in `Accounts/`.
*   *Note: A startup can be both a Deal and an Account.*

### The Inbox
The `Inbox/` folder in your data vault is the raw capture queue. Drop unprocessed analyses, meeting scraps, or drafts there and tell the agent to process the item into durable records such as `Notes`, `Activities`, `Tasks`, or `Leads`.

### Legacy Notes Migration
Legacy `Notes/` content should no longer be treated as a generic inbox. Use [legacy-notes-migration-v4.md](/Users/johnjanuszczak/Projects/crm-logic/docs/legacy-notes-migration-v4.md) to decide whether an old file stays a durable `Note`, should become an `Activity`, or would be better handled as a transient `Inbox` capture.

### The Wikilink Property Standard (CRITICAL)
All wikilinks in YAML frontmatter must be wrapped in double quotes to be functional in Obsidian:
`account: "[[Account Name]]"`

### Automatic Bookkeeping
Every write operation to the data vault triggers an automatic `git add` and `git commit` within the `$CRM_DATA_PATH` to ensure a permanent audit trail.

---

## 📂 Directory Structure (Logic)
*   `.gemini/skills/`: Specialized instruction sets for the agent.
*   `templates/`: Markdown templates for all entities.
*   `scripts/`: Core Python engines (`intelligence-engine.py`, `matchmaker.py`, `relationship_memory.py`).
*   `examples/`: Sample v4 record files for reference and testing.
*   `.env`: Local environment configuration.
