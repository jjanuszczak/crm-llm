# Skill: Update Dashboard

## Description
Refreshes the `CRM_DATA_PATH/DASHBOARD.md` file by aggregating data from the `CRM_DATA_PATH/Opportunities/`, `CRM_DATA_PATH/Tasks/`, and `CRM_DATA_PATH/Activities/` directories. This ensures a real-time, high-level overview of the vault's state.

## Usage
`update-dashboard`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **Aggregate Opportunities:**
    *   Scan `CRM_DATA_PATH/Opportunities/`.
    *   Extract `opportunity-name`, `stage`, `probability`, `close-date`, and `account`.
    *   Filter for `is-active: true`.
    *   Format into the "Active Opportunities" table.

3.  **Aggregate Tasks:**
    *   Scan `CRM_DATA_PATH/Tasks/`.
    *   Filter for `status: todo` or `status: in-progress`.
    *   Sort by `due-date` (ascending).
    *   Format into the "Upcoming Tasks" table.

4.  **Synthesize Insights:**
    *   Review recent files in `CRM_DATA_PATH/Activities/` (last 7 days).
    *   Identify strategic shifts, momentum changes, or new "Engagement Hooks."
    *   Update the "Strategic Insights" section.

5.  **Audit Suggestions:**
    *   Cross-reference "Next Steps" in Opportunities and Tasks.
    *   Propose new tasks based on missing Due Diligence (Accounts) or pending intro calls.

6.  **File Update:**
    *   Overwrite `CRM_DATA_PATH/DASHBOARD.md` with the refreshed content.
    *   Update the "Last Updated" timestamp.

7.  **Automatic Bookkeeping:**
    *   Commit the updated dashboard to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add DASHBOARD.md && git commit -m "agent: updated dashboard"
        ```

8.  **Output:**
    *   Confirm the dashboard update to the user.
