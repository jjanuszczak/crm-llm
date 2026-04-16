# Skill: CRM Create Task

## Description
Creates a current-operating-model `Task` record. Prefer the opportunity manager’s `spawn-task` path when the task belongs to an `Opportunity`; otherwise create the task directly from the task template with the current task-state conventions.

## Usage
`crm-create-task --name "Follow up with Jane" --opportunity "Opportunities/Example-Capital-Advisory-2026" --due-date "2026-04-10"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. If the task belongs to an existing opportunity, prefer [opportunity_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-opportunity-manager/scripts/opportunity_manager.py) `spawn-task`.
3. Otherwise use [task_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/task_manager.py) to create or update the record in `CRM_DATA_PATH/Tasks/`.
4. Populate:
   * `id`
   * `task-name`
   * `status`
   * `priority`
   * `owner`
   * `due-date`
   * `date-created`
   * `date-modified`
   * `primary-parent-type`
   * `primary-parent`
   * convenience links such as `account`, `contact`, `opportunity`, `lead`
   * `type`
   * `source`
   * `source-ref`
   * optional `google-task-id`
   * optional `google-task-list-id`
   * optional `email-link`
   * optional `meeting-notes`
5. Follow the live operating model for status:
   * `todo` when you owe the next move
   * `waiting` when someone else owes the next move
   * `completed` when done or clearly superseded
   * preserve other tolerated legacy values only when updating older records
6. For `waiting` tasks, set `due-date` to the next review date, not the original deadline.
7. Rebuild `index.md` and refresh the dashboard if the wider workflow does not already do so.

## Notes

- This skill should work with the repo’s current dashboard behavior, which explicitly separates actionable work from `waiting` review work.
