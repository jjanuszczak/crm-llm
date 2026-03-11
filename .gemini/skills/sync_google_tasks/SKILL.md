# Skill: Sync Google Tasks

## Description
Performs a bidirectional synchronization between the local CRM tasks (`CRM_DATA_PATH/Tasks/`) and Google Tasks using the `gws` CLI. This skill ensures that all outstanding local tasks are pushed to Google Tasks (if they don't already exist) and can optionally update local task statuses based on remote completion.

## Usage
`sync-google-tasks [--direction push|pull|both]`

## Implementation Steps

1.  **Environment Setup:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `gws` CLI is installed and authenticated.

2.  **Local Task Extraction:**
    *   Scan `CRM_DATA_PATH/Tasks/` for all `.md` files.
    *   Parse YAML frontmatter to identify tasks with `status: todo` or `status: in-progress`.
    *   Capture `task-name`, `due-date`, and `status`.

3.  **Remote Task Extraction:**
    *   Use `gws tasks tasklists list` to find the primary task list ID (usually "My Tasks").
    *   Use `gws tasks tasks list` to retrieve all uncompleted tasks from the identified list.

4.  **Deduplication & Mapping:**
    *   Compare local `task-name` with remote `title`.
    *   **Push:** Identify local tasks that do not exist remotely.
    *   **Update:** (Optional) Identify remote tasks that are marked as completed to update local files.

5.  **Execution:**
    *   For each new local task, use `gws tasks tasks insert` with the correctly formatted `due` date (RFC 3339).
    *   Log the results of the synchronization.

6.  **Automatic Bookkeeping:**
    *   If any local files were modified (e.g., status updated from remote), commit the changes to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add . && git commit -m "agent: synced tasks with Google Tasks"
        ```
    *   Run `update-dashboard`.

7.  **Output:**
    *   Summarize the number of tasks pushed, pulled, or updated.
