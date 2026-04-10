# Skill: CRM Create Deal

## Description
Creates a `Deal` inventory record for a company seeking capital. The live vault path is still `CRM_DATA_PATH/Deal-Flow/`, even though the conceptual entity name is `Deal`. Prefer the enriched wrapper [create_deal_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_deal_enriched.py), which synthesizes local CRM evidence and optional Drive/web notes before calling [deal_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/deal_manager.py).

## Usage
`crm-create-deal --name "Startup Name"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Gather the minimum real evidence first:
   * pitch materials
   * Gmail thread context
   * founder names
   * financing stage / target raise
3. Enrich the deal body before creation. Use sources in this order:
   * Local CRM first:
     * Search `Deal-Flow`, `Contacts`, `Activities`, `Opportunities`, `Tasks`, `Notes`, and linked organizations/accounts for prior fundraising context.
     * Pull out founder context, investor history, customer traction signals, and strategic fit notes already present in the vault.
   * Google Drive second:
     * Search decks, teasers, diligence docs, financial models, meeting notes, and founder materials.
     * Use Drive as the primary source for the company story, problem/solution framing, traction, previous rounds, and investor targeting.
   * Web and official sources third when needed:
     * Prefer company site, founder bios, official investor materials, product pages, and other primary sources.
     * Use web to validate stable facts or fill obvious gaps, not to invent a thesis.
4. Use [create_deal_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_deal_enriched.py) to create or update the record in the live deal directory, `CRM_DATA_PATH/Deal-Flow/`.
5. Populate canonical fields:
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
6. Synthesize and pass the unstructured body fields explicitly:
   * `--summary`
     * Clear company and fundraising summary.
   * `--problem`
     * The pain point or market gap being addressed.
   * `--solution`
     * The product, model, or operating approach solving it.
   * `--revenue-or-users`
     * Real traction signals only.
   * `--burn-rate`
     * Only if supported by evidence.
   * `--previous-rounds`
     * Prior financing history if known.
   * `--investment-highlights`
     * Reasons the deal may matter to the current CRM context.
   * `--ideal-investor-profile`
     * Investor fit framing grounded in evidence.
   * `--target-clients`
     * Relevant internal brokerage / investor targets when real.
7. Do not create a `Deal` when the real object is only a client account or advisory opportunity.
8. If the deal creates a real commercial path with an investor, add or update a linked `Opportunity`.

## Notes

- Treat this as inventory. `Opportunity` is the execution layer.
- Do not write new records to `Deals/` until the repo’s path migration is complete.
- If evidence is incomplete, leave uncertain finance fields blank rather than guessing.
