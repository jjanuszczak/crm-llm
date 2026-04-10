# Skill: CRM Create Contact

## Description
Creates a current-schema `Contact` record for a durable person relationship. Use this when a real person should exist in the CRM independently of any one email thread or meeting. Prefer the enriched wrapper [create_contact_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_contact_enriched.py), which mines local CRM context and blends optional Drive/web notes before calling [contact_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/contact_manager.py).

## Usage
`crm-create-contact --name "Jane Doe" --account "Accounts/Example-Capital"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. If the person belongs to an active commercial relationship, link the Contact to an `Account`. If the person is still pre-conversion, consider using `crm-create-lead` instead.
3. Enrich the contact before writing the body. Use sources in this order:
   * Local CRM first:
     * Search `Contacts`, `Organizations`, `Accounts`, `Activities`, `Opportunities`, `Tasks`, and `Notes` for prior interaction history and role context.
     * Pull stable details such as role, focus, repeated relationship themes, and any high-signal meeting observations.
   * Google Drive second when relevant:
     * Search pitch decks, meeting notes, org charts, diligence files, and shared documents mentioning the person.
     * Use Drive for role details, mandate, background, and any durable strategic context.
   * Web and official sources third when needed:
     * Prefer LinkedIn, company team pages, official bios, conference pages, and first-party profiles.
     * Use web only for stable role/background facts or missing public profile details.
4. Use [create_contact_enriched.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/create_contact_enriched.py) to create or update the record in `CRM_DATA_PATH/Contacts/`.
5. Populate current-schema fields:
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
6. Do not write legacy aliases such as `full--name`, `phone`, or `title` into new records.
7. Synthesize the body and pass it into the contact manager fields:
   * `--role`
     * Current role grounded in evidence.
   * `--expertise`
     * Real areas of expertise or mandate.
   * `--focus`
     * Current professional focus.
   * `--insight-1` and `--insight-2`
     * Durable, high-signal facts worth remembering.
   * `--hook-1` and `--hook-2`
     * Conversation hooks only when they are real, specific, and useful.
8. Keep contact bodies useful but stable:
   * role / focus
   * a few durable insights
   * hooks only when supported by evidence
   * avoid temporary meeting minutiae better stored in `Activities`
9. Refresh `index.md` and the dashboard if this is part of a broader mutation workflow.

## Notes

- If the contact came from lead conversion, prefer the lead conversion path so provenance carries forward cleanly.
- If sourcing is thin, keep the body minimal instead of fabricating role detail or hooks.
