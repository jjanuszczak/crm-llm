# Skill: CRM Create Activity

## Description
Creates a first-class `Activity` record using the v4 primary-parent model. This skill is backed by [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py) and should be the default path for logging meaningful meetings, calls, emails, and analysis.

## Usage
`crm-create-activity --title "Intro call with Jane Doe" --activity-type meeting --primary-parent-type opportunity --primary-parent "Opportunities/Example-Capital-Advisory-2026"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Read the underlying source content before creating the record.
   * Email: body/snippet, recipients, and outcome.
   * Meeting: description, attendees, location, linked notes, and result.
3. Use [record_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/record_manager.py) `create-activity`.
4. Require:
   * `title`
   * `activity-type`
   * `primary-parent-type`
   * `primary-parent`
5. Add optional `secondary-links`, `source`, `source-ref`, `email-link`, and `meeting-notes`.
6. Keep the record event-based and outcome-oriented. Enrich existing activity records instead of duplicating them.
7. Rebuild derived views only if the wider workflow does not already do so.

## Notes

- Preferred parent precedence is `Opportunity`, then `Contact`, then `Account`.
- Use this skill under `crm-daily-processing` whenever a real interaction happened and needs durable memory.
