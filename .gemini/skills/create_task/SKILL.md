# Skill: Create Task

## Description
Creates a new task file in the `Tasks/` directory. This skill ensures that follow-up actions, prep work, and administrative requirements are structured, dated, and linked to the relevant Account, Contact, or Opportunity.

## Usage
`create-task --name "Task Name" --account "Account" --contact "Contact" --opportunity "Opportunity" --due "YYYY-MM-DD" --priority "high|medium|low"`

## Arguments
*   `name` (Required): Short, descriptive name of the task.
*   `account` (Optional): The linked Account.
*   `contact` (Optional): The linked Contact.
*   `opportunity` (Optional): The linked Opportunity.
*   `due` (Required): Due date in `YYYY-MM-DD` format.
*   `priority` (Optional): `high`, `medium`, or `low`. Defaults to `medium`.

## Implementation Steps

1.  **File Naming:**
    *   Construct the name as `[YYYY-MM-DD] - [Task Name].md` (using the due date for chronological sorting in the folder).
    *   Verify the file does not already exist in the `Tasks/` directory.

2.  **Template Population:**
    *   Load `Templates/task-template.md`.
    *   Replace placeholders (`{{Task Name}}`, `{{Account}}`, `{{YYYY-MM-DD}}`, etc.) with provided arguments.
    *   Set `date-created` and `date-modified` to the current date (YYYY-MM-DD).
    *   Ensure wikilinks are correctly formatted (e.g., `account: "[[Account Name]]"`).

3.  **File Creation:**
    *   Write the content to `Tasks/[File Name].md`.

4.  **Output:**
    *   Confirm the file creation to the user and display the path.
