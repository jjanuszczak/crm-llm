# Skill: CRM Create Inbox Item

## Description
Creates and processes first-class `Inbox` items for raw capture that is not yet ready to become durable CRM memory. This skill is backed by [inbox_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/inbox_manager.py).

## Usage
- `crm-create-inbox-item --title "Raw notes from Jane meeting" --content "..."`
- `process-inbox-item "Raw-notes-from-Jane-meeting" --outputs note activity`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Use [inbox_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/inbox_manager.py) to create the raw item in `CRM_DATA_PATH/Inbox/`.
3. Supported outputs during processing:
   * `Note`
   * `Activity`
   * `Task`
   * `Lead`
4. Require a real primary parent when producing a `Note` or `Activity`.
5. After processing, mark the Inbox item `processed` or otherwise clear it from the active queue.

## Notes

- Use Inbox for ambiguous raw capture, not for information that is already clearly an Activity or Task.
