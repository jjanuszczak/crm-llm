# Skill: CRM Create Account

## Description
Creates a current-schema `Account` record as the commercial relationship wrapper around an existing or newly created `Organization`. Use the enriched wrapper [create_account_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_account_enriched.py) so local CRM evidence and optional Drive/web notes are synthesized before the underlying [account_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/account_manager.py) write.

## Usage
`crm-create-account --organization "Example Capital"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Ensure the canonical `Organization` exists first.
   * Prefer [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py) or `crm-create-organization`.
3. Gather relationship evidence before writing the body. Use sources in this order:
   * Local CRM first:
     * Search `Accounts`, `Organizations`, `Contacts`, `Activities`, `Opportunities`, `Tasks`, and `Notes` for current and historical relationship context.
     * Pull out stage cues, stakeholder surface area, prior introductions, execution blockers, and what makes the account strategically important.
   * Google Drive second when relevant:
     * Search for meeting notes, proposals, decks, commercial papers, diligence materials, and working docs tied to the organization or relationship.
     * Use Drive to extract stable account-level context, current lifecycle framing, and active commercial themes.
   * Web and official sources third when local evidence is insufficient:
     * Prefer the company website, investor pages, product pages, and other first-party materials.
     * Use web only to fill durable commercial context, not speculative commentary.
4. Use [create_account_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_account_enriched.py) to create the Account in `CRM_DATA_PATH/Accounts/`.
5. Populate only current relationship-layer fields:
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
6. Do not add deprecated identity fields such as `company-name`, `industry`, `size`, `url`, `investment-mandate`, or `check-size`.
7. Synthesize the body from evidence and pass it into the account manager fields:
   * `--summary`
     * Current commercial relationship summary and what matters now.
   * `--lifecycle`
     * Why this account is in the pipeline, current stage, and recent progress.
   * `--importance-notes`
     * Why this organization matters commercially or strategically over time.
   * `--execution-notes`
     * Active constraints, stakeholder dynamics, and next-step framing.
   * `--open-questions`
     * What still needs to be learned or validated.
8. Keep account bodies relationship-specific:
   * Put stable company identity in the `Organization`.
   * Put deal execution in `Opportunity`.
   * Put only the live commercial wrapper and durable account context here.
9. Rebuild `index.md` and refresh the dashboard.

## Notes

- If the record originates from a lead, prefer `crm-create-lead` plus conversion instead of hand-creating the Account.
- `Organization` owns identity. `Account` owns the live commercial relationship.
- If evidence is thin, keep the body concise and factual rather than inventing commercial narrative.
