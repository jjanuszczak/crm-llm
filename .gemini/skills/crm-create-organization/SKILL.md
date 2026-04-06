# Skill: CRM Create Organization

## Description
Creates a stable `Organization` record using the current schema. This skill is backed by [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py).

## Usage
`crm-create-organization --name "Example Capital" --organization-class investor`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Use [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py) `create`.
3. Populate stable identity fields only:
   * `id`
   * `organization-name`
   * `domain`
   * `headquarters`
   * `industry`
   * `size`
   * `url`
   * `organization-class`
   * `organization-subtype`
   * `investment-mandate`
   * `check-size`
   * `last-contacted`
   * `source`
   * `source-ref`
   * `date-created`
   * `date-modified`
4. Do not add relationship-layer execution fields here.
5. Refresh navigation artifacts if this is part of a live mutation workflow.

## Notes

- `Organization` is identity. `Account` is the commercial relationship wrapper.
