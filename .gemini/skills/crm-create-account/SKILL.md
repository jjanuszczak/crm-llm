# Skill: CRM Create Account

## Description
Creates a current-schema `Account` record as the commercial relationship wrapper around an existing or newly created `Organization`. Use this as a supporting workflow under `crm-daily-processing`, lead conversion, or opportunity setup.

## Usage
`crm-create-account --organization "Example Capital"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Ensure the canonical `Organization` exists first.
   * Prefer [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py) or `crm-create-organization`.
3. Use [account_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/account_manager.py) to create or update the Account in `CRM_DATA_PATH/Accounts/`.
4. Populate only current relationship-layer fields:
   * `id`
   * `organization`
   * `owner`
   * `relationship-stage`
   * `stage` as compatibility mirror
   * `strategic-importance`
   * `source`
   * `source-ref`
   * `source-lead` when relevant
   * `last-contacted`
   * `date-created`
   * `date-modified`
5. Do not add deprecated identity fields such as `company-name`, `industry`, `size`, `url`, `investment-mandate`, or `check-size`.
6. Write concise body sections focused on relationship context, current lifecycle, and execution notes.
7. Rebuild `index.md` and refresh the dashboard.

## Notes

- If the record originates from a lead, prefer `crm-create-lead` plus conversion instead of hand-creating the Account.
- `Organization` owns identity. `Account` owns the live commercial relationship.
