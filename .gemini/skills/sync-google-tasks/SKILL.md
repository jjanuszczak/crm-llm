# Skill: Sync Google Tasks

## Description
Performs a bidirectional synchronization between the local CRM tasks (`CRM_DATA_PATH/Tasks/`) and Google Tasks using the `gws` CLI. 

This skill ensures:
1.  **Push New:** Local `todo` tasks are created in Google Tasks.
2.  **Pull Completion:** If a task is marked completed in Google, it is marked completed locally.
3.  **Push Completion:** If a task is marked completed locally, it is marked completed in Google.

## Usage
`sync-google-tasks`

## Implementation Steps

1.  **Environment Setup:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `gws` CLI is installed and authenticated.

2.  **Local Task Extraction:**
    *   Scan `CRM_DATA_PATH/Tasks/` for all `.md` files.
    *   Parse YAML frontmatter for `task-name`, `due-date`, and `status`.

3.  **Remote Task Extraction:**
    *   Retrieve the primary task list (e.g., "My Tasks").
    *   Retrieve all tasks from Google (including hidden/completed ones) using `showCompleted: true` and `showHidden: true`.

4.  **Deduplication & Mapping:**
    *   Map remote tasks by title to a list of `{id, status}` objects to handle duplicates.

5.  **Execution Logic:**
    *   **New Local -> Google:** If local status is active but no remote version exists, `insert` into Google.
    *   **Remote Done -> Local:** If local status is active but at least one remote version is `completed`, update local to `completed`.
    *   **Local Done -> Remote:** If local status is `completed` but one or more remote versions are still `needsAction`, `patch` those remote tasks to `completed`.

6.  **Automatic Bookkeeping:**
    *   Commit local changes to the nested data repository.
    *   Run `update-dashboard`.

7.  **Output:**
    *   Display counts for: Pushed (New), Updated Local (Pull), and Updated Remote (Push).
