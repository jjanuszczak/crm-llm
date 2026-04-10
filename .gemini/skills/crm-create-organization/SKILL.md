# Skill: CRM Create Organization

## Description
Creates a stable `Organization` record using the current schema. This skill should prefer the enriched wrapper [create_organization_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_organization_enriched.py), which then calls [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py).

## Usage
`crm-create-organization --name "Example Capital" --organization-class investor`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Gather stable identity facts for frontmatter:
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
3. Enrich the unstructured body before creation. Use sources in this order:
   * Local CRM first:
     * Search existing `Organizations`, `Accounts`, `Contacts`, `Activities`, `Opportunities`, `Tasks`, and `Notes` for mentions of the organization.
     * Mine stable facts, existing relationship context, counterparties, and recurring themes.
   * Google Drive second when relevant:
     * Search for decks, notes, white papers, diligence docs, and meeting notes that mention the organization.
     * Use Drive to extract stable company facts, ecosystem role, and strategic context that should persist beyond a single deal.
   * Web and official sources third when the organization is external-facing and stable facts are incomplete:
     * Prefer the company website, official about pages, investor pages, LinkedIn company pages, and primary materials.
     * Use web search only for stable facts, not speculative commentary.
4. Synthesize four body sections from the evidence:
   * `Identity`
     * What the organization is, what it does, where it operates, and any basic orientation facts not already obvious from frontmatter.
   * `Market Context`
     * Sector position, ecosystem role, customer segment, investor/operator classification, or relevant positioning.
   * `Relationship Signals`
     * Existing CRM interaction history, quality of contact surface, known champions, and whether there is already active context in the vault.
   * `Strategic Notes`
     * Durable facts worth preserving independently of any single open opportunity.
5. Use [create_organization_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_organization_enriched.py), which synthesizes enrichment and passes both frontmatter fields and the four body fields into [organization_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/organization_manager.py):
   * `--identity`
   * `--market-context`
   * `--relationship-signals`
   * `--strategic-notes`
6. Keep organization records stable:
   * Do not put execution-layer deal tactics, temporary meeting minutiae, or per-opportunity asks in the organization body unless they are genuinely durable.
   * `Organization` is still identity and context; `Account` and `Opportunity` remain the commercial wrappers.
7. Refresh navigation artifacts if this is part of a live mutation workflow.

## Notes

- `Organization` is identity. `Account` is the commercial relationship wrapper.
- If evidence is thin, create the organization with conservative frontmatter and leave uncertain body sections brief rather than inventing detail.
- When multiple sources disagree, prefer official first-party sources for identity facts and the CRM for relationship facts.
