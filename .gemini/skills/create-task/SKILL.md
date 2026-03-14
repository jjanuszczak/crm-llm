# Skill: Create Task

## Description
Creates a new task file in the `CRM_DATA_PATH/Tasks/` directory. This skill ensures that follow-up actions, prep work, and administrative requirements are structured, dated, and linked using the v4 Task model.

## Usage
`create-task --name "Task Name" --account "Account" --contact "Contact" --opportunity "Opportunity" --due "YYYY-MM-DD" --priority "high|medium|low" --email-link "URL" --meeting-notes "URL"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **File Naming:**
    *   Construct the name as `[YYYY-MM-DD] - [Task Name].md` (using the due date for chronological sorting in the folder).
    *   Verify the file does not already exist in the `CRM_DATA_PATH/Tasks/` directory.

3.  **Template Population:**
    *   Load `templates/task-template.md`.
    *   Replace placeholders (`{{Task Name}}`, `{{Account}}`, `{{YYYY-MM-DD}}`, etc.) with provided arguments.
    *   Populate:
        *   `id`
        *   `owner`
        *   `primary-parent-type`
        *   `primary-parent`
        *   `source`
        *   `source-ref`
    *   **Email Link:** If `--email-link` is provided, populate the `email-link` field in the frontmatter.
    *   **Meeting Notes:** If `--meeting-notes` is provided, populate the `meeting-notes` field in the frontmatter.
    *   Set `date-created` and `date-modified` to the current date (YYYY-MM-DD).
    *   Ensure wikilinks are correctly formatted (e.g., `account: "[[Account Name]]"`).
    *   Support explicit `lead` links where relevant.
    *   Use the primary-parent model as canonical, while preserving convenience links to `account`, `contact`, `opportunity`, and `lead`.

4.  **Status Model:**
    *   Preferred task statuses are:
        *   `todo`
        *   `in-progress`
        *   `blocked`
        *   `done`
        *   `canceled`

5.  **File Creation:**
    *   Write the content to `CRM_DATA_PATH/Tasks/[File Name].md`.

6.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add "Tasks/[File Name].md" && git commit -m "agent: created task [Task Name]"
        ```
    *   Run `update-dashboard` to reflect the new task.

7.  **Output:**
    *   Confirm the file creation to the user and display the path.
