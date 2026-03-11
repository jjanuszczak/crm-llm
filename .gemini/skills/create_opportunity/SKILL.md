# Skill: Create Opportunity

## Description
Creates a new opportunity file in the `CRM_DATA_PATH/Opportunities/` directory. This skill follows the `Templates/opportunity-template.md` structure and ensures consistent naming and metadata tracking for sales deals.

## Usage
`create-opportunity --account "Account Name" --product "Product Name" --year "YYYY"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **File Naming:**
    *   Construct the name as `[Account] - [Product/Service] - [YYYY]`.
    *   Example: `Example Bank - Strategic Advisory - 2026.md`.
    *   Verify the file does not already exist in the `CRM_DATA_PATH/Opportunities/` directory.

3.  **Template Population:**
    *   Load `Templates/opportunity-template.md`.
    *   Replace placeholders (`{{Account}}`, `{{Product/Service}}`, `{{YYYY}}`, etc.) with provided arguments.
    *   Ensure the `account` property in the YAML frontmatter is correctly wikilinked: `account: "[[Account Name]]"`.
    *   Set `date-created` and `date-modified` to the current date (YYYY-MM-DD).
    *   Default `stage` to `discovery` and `probability` to `10`.
    *   Default `is-active` to `true`.

4.  **Contextual Enrichment:**
    *   Wikilink the `account` and `primary-contact` correctly.
    *   If details about the stakeholder roles (Economic Buyer, Champion) are known from the account or recent activities, populate the "Stakeholder Management" section.

5.  **File Creation:**
    *   Write the content to `CRM_DATA_PATH/Opportunities/[Opportunity Name].md`.

6.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add "Opportunities/[Opportunity Name].md" && git commit -m "agent: created opportunity [Opportunity Name]"
        ```
    *   Run `update-dashboard` to reflect the new opportunity.

7.  **Output:**
    *   Confirm the file creation to the user and display the path.
