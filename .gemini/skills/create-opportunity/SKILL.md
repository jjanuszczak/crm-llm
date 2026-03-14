# Skill: Create Opportunity

## Description
Creates a new opportunity file in the `CRM_DATA_PATH/Opportunities/` directory. This skill follows the v4 Opportunity model and ensures consistent naming, provenance, and structured stakeholder metadata for active engagements.

## Usage
`create-opportunity --account "Account Name" --product "Product Name" --year "YYYY"`
## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **LinkedIn Stakeholder Mapping (Warm Path Discovery):**
    *   **Trigger:** If an account is provided, search LinkedIn for the company page.
    *   **Extraction:** Identify key decision-makers (CXOs, Heads of Digital/Partnerships).
    *   **Graph Matching:** Cross-reference extracted names against `CRM_DATA_PATH/Contacts/`.
    *   **Warm Path Identification:** If a match is found (e.g., "I already have a relationship with the CIO of Account [X]"), stage this in `CRM_DATA_PATH/staging/warm_paths.json`.

3.  **File Naming:**
...

    *   Construct the name as `[Account] - [Product/Service] - [YYYY]`.
    *   Example: `Example Bank - Strategic Advisory - 2026.md`.
    *   Verify the file does not already exist in the `CRM_DATA_PATH/Opportunities/` directory.

3.  **Template Population:**
    *   Load `templates/opportunity-template.md`.
    *   Replace placeholders (`{{Account}}`, `{{Product/Service}}`, `{{YYYY}}`, etc.) with provided arguments.
    *   Populate:
        *   `id`
        *   `owner`
        *   `source`
        *   `source-ref`
        *   `source-lead` when the Opportunity originates from a converted Lead
        *   `opportunity-type`
    *   Ensure the `account` property in the YAML frontmatter is correctly wikilinked: `account: "[[Account Name]]"`.
    *   Set `date-created` and `date-modified` to the current date (YYYY-MM-DD).
    *   Default `stage` to `discovery` and `probability` to `10`.
    *   Default `is-active` to `true`.
    *   Populate `commercial-value` and keep `deal-value` aligned for backward compatibility until older repo logic is fully migrated.

4.  **Contextual Enrichment:**
    *   Wikilink the `account` and `primary-contact` correctly.
    *   If details about the stakeholder roles (Economic Buyer, Champion) are known from the account or recent activities, populate the "Stakeholder Management" section.
    *   Add known stakeholder links such as `influencers` into structured frontmatter where possible.

5.  **File Creation:**
    *   Write the content to `CRM_DATA_PATH/Opportunities/[Opportunity Name].md`.

6.  **Compatibility Note:**
    *   `commercial-value` is the clearer v4 field.
    *   `deal-value` should still be populated in parallel until older repo logic is fully migrated.

7.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add "Opportunities/[Opportunity Name].md" && git commit -m "agent: created opportunity [Opportunity Name]"
        ```
    *   Run `update-dashboard` to reflect the new opportunity.

8.  **Output:**
    *   Confirm the file creation to the user and display the path.
