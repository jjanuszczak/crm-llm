# Skill: Create Activity

## Description
Creates a first-class activity file in the `CRM_DATA_PATH/Activities/` directory using the v4 activity model. Activities track real events and interactions and must use one primary parent plus optional secondary links.

## Usage
`create-activity --title "Initial email with Jane Doe" --activity-type email --primary-parent-type opportunity --primary-parent "Opportunities/Example-Capital-Advisory-2026" --secondary-links "Contacts/Jane-Doe" "Accounts/Example-Capital" --date "YYYY-MM-DD"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **File Naming:**
    *   Construct the name from a slugified activity title.
    *   Verify the file does not already exist in the `CRM_DATA_PATH/Activities/` directory.

3.  **Template Population:**
    *   Load `templates/activity-template.md`.
    *   Replace placeholders with provided arguments.
    *   Require:
        * `activity-name`
        * `activity-type`
        * `primary-parent-type`
        * `primary-parent`
    *   Allow optional `secondary-links`.
    *   **Email Link:** If `--email-link` is provided, populate the `email-link` field in the frontmatter.
    *   **Meeting Notes:** If `--meeting-notes` is provided, populate the `meeting-notes` field in the frontmatter.
    *   Set `date-created` and `date-modified`.

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
