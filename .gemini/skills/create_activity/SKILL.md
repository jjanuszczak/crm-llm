# Skill: Create Activity

## Description
Creates a new activity file in the `CRM_DATA_PATH/Activities/` directory. This skill automates the tracking of interactions (calls, emails, meetings, etc.) and ensures they are correctly linked to contacts and opportunities using the `Templates/activity-template.md`.

## Usage
`create-activity --type "call|email|meeting|analysis|note" --contact "Contact Name" --opportunity "Opportunity Name" --date "YYYY-MM-DD"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **File Naming:**
    *   Construct the name as `[YYYY-MM-DD] - [type] - [Contact Name].md`.
    *   Example: `2026-02-19 - email - Ghazal Al Sakaal.md`.
    *   Verify the file does not already exist in the `CRM_DATA_PATH/Activities/` directory.

3.  **Template Population:**
    *   Load `Templates/activity-template.md`.
    *   Replace placeholders (`{{activity-date}}`, `{{type}}`, etc.) with provided arguments.
    *   Wikilink the `contacts` (as an array) and the `opportunity` correctly.

4.  **Content Capture:**
    *   **Outcomes:** Summarize the key results of the activity.
    *   **Detailed Notes:** Capture the discussion points, stakeholder sentiment, and raw data (like email text).
    *   **Action Items:** Extract specific follow-up tasks, assign owners, and set deadlines.
    *   **Strategic Insights:** Record any "little known" facts or strategic shifts discovered.

5.  **File Creation:**
    *   Write the content to `CRM_DATA_PATH/Activities/[Activity Name].md`.

6.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add "Activities/[Activity Name].md" && git commit -m "agent: recorded activity [Activity Name]"
        ```
    *   Run `update-dashboard` to reflect the new activity.

7.  **Output:**
    *   Confirm the file creation to the user and display the path.
