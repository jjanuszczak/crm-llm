# Skill: CRM Create Deal

## Description
Creates a `Deal` inventory record for a company seeking capital. The live vault path is still `CRM_DATA_PATH/Deal-Flow/`, even though the conceptual entity name is `Deal`.

## Usage
`crm-create-deal --name "Startup Name"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Gather the minimum real evidence first:
   * pitch materials
   * Gmail thread context
   * founder names
   * financing stage / target raise
3. Use [deal_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/deal_manager.py) to create or update the record in the live deal directory, `CRM_DATA_PATH/Deal-Flow/`.
4. Populate canonical fields:
   * `id`
   * `startup-name`
   * `owner`
   * `sector`
   * `fundraising-stage`
   * `coverage-status`
   * `location`
   * `traction-metrics`
   * `target-raise`
   * `currency`
   * `valuation-cap`
   * `pitch-deck-url`
   * `google-drive-url`
   * `founder-contacts`
   * `related-accounts`
   * `related-opportunities`
   * `source`
   * `source-ref`
   * `date-sourced`
   * `date-modified`
5. Do not create a `Deal` when the real object is only a client account or advisory opportunity.
6. If the deal creates a real commercial path with an investor, add or update a linked `Opportunity`.

## Notes

- Treat this as inventory. `Opportunity` is the execution layer.
- Do not write new records to `Deals/` until the repo’s path migration is complete.
