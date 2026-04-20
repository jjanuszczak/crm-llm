---
name: crm-nightly-task-report
description: Create a nightly CRM task report listing overdue tasks and tasks due in the next few days from CRM_DATA_PATH/Tasks, grouped by overdue/upcoming, date, status, and priority, and save it as a Markdown report.
---

# Skill: CRM Nightly Task Report

## Use When

Use this skill when the user asks for a nightly task report, overdue tasks, upcoming CRM tasks, or the report pattern "overdue or to be done in the next couple days."

## Workflow

1. Resolve `CRM_DATA_PATH` from the environment or `.env`.
2. Run the bundled script:

   ```bash
   python3 .gemini/skills/crm-nightly-task-report/scripts/nightly_task_report.py --days 3
   ```

3. Report the saved file path and summarize the top execution cluster.

## Report Rules

- Use the current local date as the report date unless the user gives a date.
- Treat `--days 3` as today plus the next three calendar days. For example, on 2026-04-20 this includes due dates through 2026-04-23.
- Exclude statuses `complete`, `completed`, `done`, and `canceled`.
- Keep `todo` separate from `waiting`; `todo` means John owes action, while `waiting` means someone else owes the next move or the item needs review.
- Prioritize high-priority `todo` tasks when summarizing the execution cluster.
- Save reports under `CRM_DATA_PATH/Reports` unless the user asks for a different destination.

## Notes

- This is a read/report workflow. It should not mutate CRM task records, `crm-data/index.md`, or `crm-data/log.md`.
- If the user asks to run this automatically every night, create a Codex automation that invokes this skill and opens an inbox item with the report path and top priorities.
