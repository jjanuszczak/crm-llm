# Skill: Update Dashboard

## Description
Refreshes the `DASHBOARD.md` file by aggregating data from the `Opportunities/`, `Tasks/`, and `Activities/` directories. This ensures a real-time, high-level overview of the vault's state.

## Usage
`update-dashboard`

## Implementation Steps

1.  **Aggregate Opportunities:**
    *   Scan `Opportunities/`.
    *   Extract `opportunity-name`, `stage`, `probability`, `close-date`, and `account`.
    *   Filter for `is-active: true`.
    *   Format into the "Active Opportunities" table.

2.  **Aggregate Tasks:**
    *   Scan `Tasks/`.
    *   Filter for `status: todo` or `status: in-progress`.
    *   Sort by `due-date` (ascending).
    *   Format into the "Upcoming Tasks" table.

3.  **Synthesize Insights:**
    *   Review recent files in `Activities/` (last 7 days).
    *   Identify strategic shifts, momentum changes, or new "Engagement Hooks."
    *   Update the "Strategic Insights" section.

4.  **Audit Suggestions:**
    *   Cross-reference "Next Steps" in Opportunities and Tasks.
    *   Propose new tasks based on missing Due Diligence (Accounts) or pending intro calls.

5.  **File Update:**
    *   Overwrite `DASHBOARD.md` with the refreshed content.
    *   Update the "Last Updated" timestamp.
