# Skill: Update Dashboard

## Description
Refreshes the `CRM_DATA_PATH/DASHBOARD.md` file as a relationship-first home view. It prioritizes relationships needing attention, recently active/heating-up relationships, qualified leads, and recommended next actions while still keeping a compact opportunity snapshot and recent memory view.

## Usage
`update-dashboard [--skip-followups] [--skip-commit]`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **Assemble Relationship Context:**
    *   Scan `CRM_DATA_PATH/Accounts/`, `Contacts/`, `Opportunities/`, `Leads/`, `Tasks/`, `Activities/`, and `Notes/`.
    *   Normalize legacy bare links, path-qualified wikilinks, and slug-style links so older records still connect.
    *   Build relationship candidates around active opportunities using linked account, primary contact, tasks, activities, and notes.

3.  **Score Dashboard Sections:**
    *   `Relationships Needing Attention`: rank by a composite attention score using warmth, priority, overdue work, due-soon work, and opportunity signal.
    *   `Recently Active / Heating Up`: rank by recent activity and velocity.
    *   `Qualified Leads / Near Conversion`: show only `qualified` leads.
    *   `Recommended Next Actions`: rank open tasks by due date, priority, and linked opportunity probability.

4.  **Render Supporting Views:**
    *   Add a compact active opportunities snapshot.
    *   Add a recent memory section combining Notes and Activities.
    *   Generate a short summary section from the highest-signal relationship and execution items.

5.  **File Update:**
    *   Overwrite `CRM_DATA_PATH/DASHBOARD.md` with the refreshed v4 relationship-first dashboard.
    *   Update the "Last Updated" timestamp.

6.  **Optional Follow-Ups:**
    *   Unless `--skip-followups` is passed, run `matchmaker.py` and `intelligence-engine.py`.
    *   Unless `--skip-commit` is passed, commit only scoped generated outputs in the nested CRM data repo.
    *   Do not sweep unrelated vault files into the commit.

7.  **Output:**
    *   Confirm the dashboard update to the user and note whether follow-ups/commit were skipped.
