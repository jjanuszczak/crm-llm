# Skill: CRM Create Opportunity

## Description
Creates a canonical `Opportunity` and related sub-records using the current opportunity manager. This is the preferred creation path for real commercial or strategic execution work.

## Usage
`crm-create-opportunity --account "Account Name" --primary-contact "Contacts/Jane-Doe" --product-service "Strategic Advisory"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Use [opportunity_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-opportunity-manager/scripts/opportunity_manager.py) `create`.
3. Populate current-schema fields:
   * `id`
   * `opportunity-name`
   * `owner`
   * `date-created`
   * `date-modified`
   * `account`
   * optional `deal`
   * `primary-contact`
   * optional `source-lead`
   * `organization`
   * `opportunity-type`
   * `is-active`
   * `stage`
   * `commercial-value`
   * `close-date`
   * `probability`
   * `product-service`
   * `influencers`
   * `source`
   * `source-ref`
4. Keep `deal-value` mirrored only where existing scripts still require compatibility.
5. After creation, use `spawn-task`, `spawn-activity`, or `spawn-note` for the obvious next linked records.

## Notes

- Prefer this over raw hand-authored opportunity files.
- Use this as a supporting workflow under `crm-daily-processing`, `crm-create-lead` conversion, or relationship review.
