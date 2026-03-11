# CRM Logic: Agentic Venture Brokerage & Personal CRM

This repository contains the **Logic and Automation** for a personal agentic CRM system. It is designed to work with the [Gemini CLI](https://github.com/google/gemini-cli) to automate due diligence, deal tracking, and workspace synchronization.

## 🏗 Architecture: The "Nested Repo" Strategy

This project follows a **decoupled architecture**:
*   **Logic (This Repo):** Contains the skills, scripts, templates, and instructions for the agent. This is public-friendly.
*   **Data (Private Vault):** Your actual CRM data (Accounts, Contacts, etc.) is stored in a separate directory (e.g., `crm-data/`) which is a standalone Git repository. This directory is nested within the logic repo but ignored by its version control.

This strategy allows the agent to use native file tools (`read_file`, `write_file`) while keeping your private data securely isolated.

---

## 🚀 Getting Started

### 1. Prerequisites
*   **[Gemini CLI](https://github.com/google/gemini-cli)** installed and authenticated.
*   **[GWS CLI](https://github.com/googleworkspace/cli)** installed and authenticated (required for Google Tasks sync).
*   **Python 3.x** for dashboarding and sync scripts.
*   **Obsidian** (Optional) for a rich UI to view your data.

### 2. Installation
Clone this repository and move into the directory:
```bash
git clone <this-repo-url> crm-logic
cd crm-logic
```

### 3. Initialize your Data Vault
Create a new private data repository using the built-in skill:
```bash
# This creates the folder structure and initializes a separate git repo
python3 .gemini/skills/init-crm-data/scripts/init-vault.py my-crm-data
```

### 4. Configuration
Create a `.env` file in the root directory:
```text
CRM_DATA_PATH=./my-crm-data
```

---

## 🛠 Available Skills

The agent can perform the following automated workflows:

| Skill | Command | Description |
| :--- | :--- | :--- |
| **Init Vault** | `init-crm-data <name>` | Sets up a new nested data repository. |
| **Dashboard** | `update-dashboard` | Refreshes `DASHBOARD.md` with active pipeline & tasks. |
| **Workspace Sync** | `sync-workspace` | Scans Gmail/Calendar for updates on active contacts. |
| **Task Sync** | `sync-google-tasks` | Bidirectional sync with Google Tasks via `gws` CLI. |
| **Account DD** | `create-account` | Researches a company and generates a DD report. |
| **Contact Bio** | `create-contact` | Researches professional bios and engagement hooks. |
| **Opportunities**| `create-opportunity` | Initiates deal tracking for a specific account. |
| **Deal Flow** | `create-deal` | Captures startup inventory from Drive/Gmail/Web. |

---

## 📋 Operational Protocols

### The State-Change Hook (Automatic Bookkeeping)
Every time the agent creates or modifies a file in your data vault, it follows a strict protocol:
1.  **Update Metadata:** Refreshes the `date-modified` field in the file's YAML frontmatter.
2.  **Commit Change:** Automatically commits the change *within* the data subdirectory:
    ```bash
    cd $CRM_DATA_PATH && git add . && git commit -m "agent: [action]"
    ```
3.  **Refresh UI:** Runs `update-dashboard` to ensure your overview is current.

---

## 📂 Directory Structure (Logic)
*   `.gemini/skills/`: Specialized instruction sets for the agent.
*   `Templates/`: Markdown templates for Accounts, Contacts, Tasks, etc.
*   `scripts/`: Shared utility scripts (e.g., note indexing).
*   `.env`: Local environment configuration.
