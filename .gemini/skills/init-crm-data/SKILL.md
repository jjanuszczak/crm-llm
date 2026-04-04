# Skill: Init CRM Data

## Description
Initializes a new CRM data repository as a nested subdirectory within the `crm-logic` project. This skill ensures the new vault follows the standard folder structure, is initialized as a separate git repository, and is correctly ignored by the main project's version control.

## Usage
`init-crm-data <directory-name>`

## Implementation Steps

1.  **Directory Creation:**
    *   Create the target directory (e.g., `client-x-data`).
    *   Verify the directory is within the `crm-logic` root.

2.  **Folder Structure:**
    *   Create the following standard subdirectories:
        *   `Organizations/`
        *   `Accounts/`
        *   `Contacts/`
        *   `Leads/`
        *   `Opportunities/`
        *   `Deals/`
        *   `Activities/`
        *   `Notes/`
        *   `Inbox/`
        *   `Tasks/`
        *   `Reports/`
        *   `.obsidian/` (to support the Obsidian UI)

3.  **Git Initialization:**
    *   Run `git init` inside the new directory.
    *   Create a local `.gitignore` within the new directory (e.g., ignoring `.DS_Store`).

4.  **Main Repo Protection:**
    *   Automatically append the `<directory-name>/` to the **main project's** `.gitignore` file to ensure the nested data is never accidentally committed to the logic repo.

5.  **Initial Files:**
    *   Create an initial `DASHBOARD.md`.
    *   Create a `GEMINI_INDEX.md` for local indexing.

6.  **Environment Update (Optional):**
    *   Prompt the user if they would like to update `.env` to make this the active `CRM_DATA_PATH`.

7.  **Output:**
    *   Confirm the creation and provide instructions on how to swap to the new vault.
