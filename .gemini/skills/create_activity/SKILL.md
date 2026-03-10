# Skill: Create Activity

## Description
Creates a new activity file in the `Activities/` directory. This skill automates the tracking of interactions (calls, emails, meetings, etc.) and ensures they are correctly linked to contacts and opportunities using the `Templates/activity-template.md`.

## Usage
`create-activity --type "call|email|meeting|analysis|note" --contact "Contact Name" --opportunity "Opportunity Name" --date "YYYY-MM-DD"`

## Arguments
*   `type` (Required): The type of activity (e.g., `call`, `email`).
*   `contact` (Required): The name of the primary contact involved.
*   `opportunity` (Optional): The name of the linked opportunity.
*   `date` (Optional): The date the activity occurred. Defaults to the current date.

## Implementation Steps

1.  **File Naming:**
    *   Construct the name as `[YYYY-MM-DD] - [type] - [Contact Name].md`.
    *   Example: `2026-02-19 - email - Ghazal Al Sakaal.md`.
    *   Verify the file does not already exist in the `Activities/` directory.

2.  **Template Population:**
    *   Load `Templates/activity-template.md`.
    *   Replace placeholders (`{{activity-date}}`, `{{type}}`, etc.) with provided arguments.
    *   Wikilink the `contacts` (as an array) and the `opportunity` correctly.

3.  **Content Capture:**
    *   **Outcomes:** Summarize the key results of the activity.
    *   **Detailed Notes:** Capture the discussion points, stakeholder sentiment, and raw data (like email text).
    *   **Action Items:** Extract specific follow-up tasks, assign owners, and set deadlines.
    *   **Strategic Insights:** Record any "little known" facts or strategic shifts discovered.

4.  **File Creation:**
    *   Write the content to `Activities/[Activity Name].md`.

5.  **Output:**
    *   Confirm the file creation to the user and display the path.
