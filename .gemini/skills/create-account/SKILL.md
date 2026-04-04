# Skill: Create Account

## Description
Creates a new account file in the `CRM_DATA_PATH/Accounts/` directory for a specified organization. In the Organization-first model, `Organization` is the stable entity layer and `Account` is the commercial relationship layer.

## Usage
`create-account "Company Name" --url "https://example.com" --priority "medium"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **Organization First:**
    *   Ensure a corresponding `Organization` exists in `CRM_DATA_PATH/Organizations/`.
    *   If not, create it first using `create-organization`.
    *   Then create the `Account` record linked to that organization.

3.  **Web Research:**
    *   **Search 1:** Google search for `"[Company Name]" headquarters industry revenue headcount 2025 2026` to find frontmatter data.
    *   **Search 2:** Google search for `"[Company Name]" strategic due diligence report news 2025 2026` to find recent business developments.
    *   **Search 3:** Google search for `"[Company Name]" leadership founders funding investors` to find structural information.
    *   **Search 4:** Google search for `"[Company Name]" competitors Gartner Peer Insights G2 reviews` to find market positioning.

4.  **Content Generation (Using `templates/account-template.md`):**
    *   **Frontmatter:**
        *   `id`: Stable machine-friendly account ID.
        *   `organization`: Link to the canonical organization record.
        *   `owner`: Default to the primary operator.
        *   `relationship-stage`: Default to `prospect`.
        *   `stage`: Keep in sync with `relationship-stage` for backward compatibility while older workflows still reference it.
        *   `strategic-importance`: Stable relationship importance (`high|medium|low`).
        *   `source`: Default to `manual` unless the account is created from a clearer origin such as `lead-conversion`.
        *   `source-ref`: Optional provenance link, especially when the Account is created from lead conversion or discovery review.
        *   `last-contacted`: Persist the latest observed interaction date.
        *   `date-created`: Current date (YYYY-MM-DD).
        *   `date-modified`: Current date (YYYY-MM-DD).
    *   **Body Sections:**
        *   Focus the body on relationship context, strategic importance, and execution notes.
        *   Stable identity and investor-profile facts belong on the linked Organization record rather than the Account.

5.  **File Creation:**
    *   Write the generated content to `CRM_DATA_PATH/Accounts/[Company-Name].md`.

6.  **Compatibility Note:**
    *   `relationship-stage` is the clearer v4 relationship-state field.
    *   `stage` should still be populated in parallel until older repo logic is fully migrated.
    *   Do not persist computed execution-priority or `days-since-contact` on the Account.

7.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add Accounts/[Company-Name].md && git commit -m "agent: created account [Company-Name]"
        ```
    *   Run `update-dashboard` to reflect the new account.

8.  **Output:**
    *   Confirm the file creation to the user and display the path.
