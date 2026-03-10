# Skill: Create Opportunity

## Description
Creates a new opportunity file in the `Opportunities/` directory. This skill follows the `Templates/opportunity-template.md` structure and ensures consistent naming and metadata tracking for sales deals.

## Usage
`create-opportunity --account "Account Name" --product "Product Name" --year "YYYY"`

## Arguments
*   `account` (Required): The name of the account the opportunity is linked to.
*   `product` (Required): The specific product or service being offered (e.g., "BaaS Expansion").
*   `year` (Optional): The year of the opportunity. Defaults to the current year.

## Implementation Steps

1.  **File Naming:**
    *   Construct the name as `[Account] - [Product/Service] - [YYYY]`.
    *   Example: `Example Bank - Strategic Advisory - 2026.md`.
    *   Verify the file does not already exist in the `Opportunities/` directory.

2.  **Template Population:**
    *   Load `Templates/opportunity-template.md`.
    *   Replace placeholders (`{{Account}}`, `{{Product/Service}}`, `{{YYYY}}`, etc.) with provided arguments.
    *   Ensure the `account` property in the YAML frontmatter is correctly wikilinked: `account: "[[Account Name]]"`.
    *   Set `date-created` and `date-modified` to the current date (YYYY-MM-DD).
    *   Default `stage` to `discovery` and `probability` to `10`.
    *   Default `is-active` to `true`.

3.  **Contextual Enrichment:**
    *   Wikilink the `account` and `primary-contact` correctly.
    *   If details about the stakeholder roles (Economic Buyer, Champion) are known from the account or recent activities, populate the "Stakeholder Management" section.

4.  **File Creation:**
    *   Write the content to `Opportunities/[Opportunity Name].md`.

5.  **Output:**
    *   Confirm the file creation to the user and display the path.
