# Skill: Create Daily Report

## Description
Generates a comprehensive summary of all strategic actions, CRM updates, and communications performed during the current session and saves it as a Markdown file in the `CRM_DATA_PATH/Reports/` directory. This skill ensures that daily accomplishments are documented and aligned with the three core business pillars.

## Usage
`create-daily-report`

## Implementation Steps

1.  **Session Synthesis:**
    *   Review the entire conversation history of the current session.
    *   Categorize actions into the three core pillars:
        1.  **Deals (Inventory & Strategy):** Startups, fundraising, deal flow.
        2.  **Accounts (Entities & Partners):** Investors, corporates, institutional partners.
        3.  **Opportunities (Transactions & Advisory):** Active engagements and transactions.
    *   Identify administrative updates (email scans, task completions).
    *   Extract key strategic insights or shifts identified during the session.

2.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify the `Reports/` directory exists within that path; create it if necessary.

3.  **File Naming:**
    *   Construct the filename as `[YYYY-MM-DD] - Progress Report.md`.
    *   Example: `2026-03-12 - Progress Report.md`.

4.  **Template Population:**
    *   Load `templates/report-template.md`.
    *   Replace `{{YYYY-MM-DD}}` with the current date.
    *   Populate the sections with the synthesized session data using professional, high-signal language.

5.  **File Creation:**
    *   Write the content to `CRM_DATA_PATH/Reports/[Filename].md`.

6.  **Automatic Bookkeeping:**
    *   Commit the new report to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add "Reports/[Filename].md" && git commit -m "agent: generated daily progress report [YYYY-MM-DD]"
        ```

7.  **Optional Email Draft:**
    *   Propose drafting an email to share this report with stakeholders (e.g., `mrs@januszczak.org`) if requested by the user.

8.  **Output:**
    *   Confirm the report creation and display the saved path.
