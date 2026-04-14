---
name: crm-log-meeting-from-notes
description: Log a scheduled or unscheduled meeting from meeting notes, usually from a Google Doc or transcript, by finding the related CRM records, updating or creating the matching Activity, inferring concrete follow-on Tasks with due dates, and refreshing index.md/log.md/dashboard artifacts.
---

# Skill: CRM Log Meeting From Notes

## Description
Use this skill when the user gives you meeting notes or a reference to meeting notes and wants you to:

- find the related CRM records
- log the meeting as an `Activity`
- infer and create follow-on `Task` records
- keep `crm-data/index.md`, `crm-data/log.md`, and dashboard-derived views current

This skill is for durable CRM capture from an actual interaction. It should work for both:

- meetings that already exist as scheduled activity stubs
- unscheduled or ad hoc meetings that need a fresh activity record

## Typical Triggers

- "Log this meeting from the notes."
- "The notes are in Google Drive. Update the CRM and create follow-up tasks."
- "I met with X yesterday. Find the notes and capture the activity."
- "Use this transcript to log the meeting and extract action items."

## Workflow

1. **Resolve the source notes**
   - If the user gives a Google Drive title or fuzzy reference, search Drive first.
   - If the user gives a Docs URL, fetch the document text directly.
   - Read the actual notes before writing anything.
   - Prefer the note source itself over calendar titles or prior CRM guesses.

2. **Orient to the CRM**
   - Resolve `CRM_DATA_PATH` dynamically.
   - Read `docs/schema-spec.md` if the write shape is unclear.
   - Read `crm-data/index.md` first to find candidate `Organization`, `Account`, `Contact`, `Opportunity`, and `Deal-Flow` records.
   - Read `crm-data/log.md` when recent mutations may affect dedupe or parent selection.

3. **Find the relationship cluster**
   - Use names, companies, and deal references in the notes to locate the relevant records.
   - Preferred primary parent precedence:
     1. `Opportunity`
     2. `Contact`
     3. `Account`
   - Add other materially relevant records as `secondary-links`.
   - Preserve live path reality such as `Deal-Flow/`.

4. **Decide whether to update or create the activity**
   - Search for an existing scheduled activity for the same meeting date, participants, or topic.
   - If a matching scheduled stub exists, update it instead of creating a duplicate.
   - If no activity exists, create one via [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py) `create-activity`.
   - Activity records should be event-based, outcome-oriented, and linked back to the note source through `source-ref` and `meeting-notes` when available.

5. **Write the activity content**
   - Set `status: completed` for meetings that happened.
   - Capture:
     - why the meeting happened
     - what was agreed
     - what changed in the commercial or relationship picture
     - concrete next actions
   - Avoid copying raw transcript chunks. Summarize into durable CRM memory.
   - If the notes mention stale assumptions already captured in the CRM, update the activity to reflect the corrected reality.

6. **Infer follow-on tasks**
   - Create tasks only for concrete next actions with a clear owner or an obvious owner implied by context.
   - Prefer `todo` when John owes the next move.
   - Prefer `waiting` when someone else owes the next move; set the `due-date` to the next review date, not the original ask date.
   - If the task belongs to an existing opportunity, prefer [task_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/task_manager.py) with `primary-parent-type=opportunity` and the relevant convenience links.
   - Do not create vague tasks like "think about strategy" unless the note gives a concrete follow-up motion.
   - Do not create duplicate tasks if an open task already captures the same action; update the existing task if needed.

7. **Infer due dates pragmatically**
   - Use explicit dates from the notes when present.
   - If the notes reference a relative date such as "Wednesday," convert it to an absolute `YYYY-MM-DD` date using the meeting date and user locale.
   - If timing is implied but not explicit, choose the earliest defensible review/action date rather than leaving the task dateless.
   - If there is no responsible due date inference that can be made, say so and skip task creation for that item.

8. **Refresh mutation artifacts**
   - Ensure the workflow appends to `crm-data/log.md`.
   - Rebuild `crm-data/index.md`.
   - Refresh dashboard-derived outputs if this workflow made durable changes.

## Output Expectations

When you use this skill, the finished result should normally include:

- one completed `Activity` record, either updated or newly created
- zero or more concrete `Task` records
- refreshed `index.md`
- appended `log.md`
- refreshed `DASHBOARD.md` when the workflow updated durable records

## Guardrails

- Always read the notes themselves before logging the meeting.
- Do not rely only on the calendar title.
- Do not duplicate an existing activity if a scheduled stub already exists.
- Do not invent parent links when the notes are not specific enough to resolve the company or deal.
- If a follow-up item clearly exists but the target entity cannot be resolved safely, mention that gap in the final response instead of guessing.
- Keep new writes canonical and tolerate legacy fields only when updating existing records.

## Useful Commands

- Create a new activity:
  - `python3 scripts/record_manager.py create-activity ...`
- Create or update a task:
  - `python3 scripts/task_manager.py create ...`
  - `python3 scripts/task_manager.py update ...`
- Append workflow history:
  - `python3 scripts/navigation_manager.py append-log ...`
- Refresh dashboard and derived views:
  - `CRM_DATA_PATH=./crm-data python3 .gemini/skills/update-dashboard/scripts/update-dashboard.py --skip-followups --skip-commit`

## Notes

- Google Drive meeting notes are often the best source for `source-ref` and `meeting-notes`.
- When the note contains multiple candidate companies, treat the meeting as a multi-record workflow and add all materially relevant records as `secondary-links`.
- The activity should preserve strategic insight, not just clerical action items.
