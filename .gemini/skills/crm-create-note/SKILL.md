# Skill: CRM Create Note

## Description
Creates a first-class durable `Note` record using the v4 primary-parent model. This skill is backed by [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py).

## Usage
`crm-create-note --title "Jane relationship context" --primary-parent-type contact --primary-parent "Contacts/Jane-Doe"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Use [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py) `create-note`.
3. Require:
   * `title`
   * `primary-parent-type`
   * `primary-parent`
4. Allow optional `secondary-links`, `source`, and `source-ref`.
5. Keep Notes durable and interpretive. If something discrete happened, log an `Activity` too or instead.

## Notes

- Notes are not inbox scratchpads.
- Preferred primary parent precedence is `Opportunity`, then `Contact`, then `Account`.
