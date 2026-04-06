# Skill: CRM Create Contact

## Description
Creates a current-schema `Contact` record for a durable person relationship. Use this when a real person should exist in the CRM independently of any one email thread or meeting.

## Usage
`crm-create-contact --name "Jane Doe" --account "Accounts/Example-Capital"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. If the person belongs to an active commercial relationship, link the Contact to an `Account`. If the person is still pre-conversion, consider using `crm-create-lead` instead.
3. Use [contact_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/contact_manager.py) to create or update the record in `CRM_DATA_PATH/Contacts/`.
4. Populate current-schema fields:
   * `id`
   * `full-name`
   * `nickname`
   * `owner`
   * `account`
   * optional `deal`
   * `linkedin`
   * `email`
   * `mobile`
   * `source`
   * `source-ref`
   * `relationship-status`
   * `priority`
   * `last-contacted`
   * `date-created`
   * `date-modified`
5. Do not write legacy aliases such as `full--name`, `phone`, or `title` into new records.
6. Keep the body useful:
   * current role / focus
   * a few stable insights
   * conversation hooks only when they are real and high-signal
7. Refresh `index.md` and the dashboard if this is part of a broader mutation workflow.

## Notes

- If the contact came from lead conversion, prefer the lead conversion path so provenance carries forward cleanly.
