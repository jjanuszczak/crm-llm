# Skill: Create Account

## Description
Creates a new account file in the `CRM_DATA_PATH/Accounts/` directory for a specified company. This skill automates file creation, populates the v4 Account frontmatter, and performs web research to generate a comprehensive strategic due diligence report.

## Usage
`create-account "Company Name" --url "https://example.com" --priority "medium"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **File Naming:**
    *   Convert the `company` to `[Company-Name].md` format (e.g., `ZingHR.md`).
    *   Check if `CRM_DATA_PATH/Accounts/[Company-Name].md` already exists. If it does, stop and notify the user.

3.  **Web Research:**
    *   **Search 1:** Google search for `"[Company Name]" headquarters industry revenue headcount 2025 2026` to find frontmatter data.
    *   **Search 2:** Google search for `"[Company Name]" strategic due diligence report news 2025 2026` to find recent business developments.
    *   **Search 3:** Google search for `"[Company Name]" leadership founders funding investors` to find structural information.
    *   **Search 4:** Google search for `"[Company Name]" competitors Gartner Peer Insights G2 reviews` to find market positioning.

4.  **Content Generation (Using `templates/account-template.md`):**
    *   **Frontmatter:**
        *   `id`: Stable machine-friendly account ID.
        *   `company-name`: The official name of the company.
        *   `owner`: Default to the primary operator.
        *   `headquarters`: City, Country.
        *   `industry`: Primary industry sector.
        *   `size`: Revenue in USD Millions, estimated commercial scale, or headcount depending on the best available signal.
        *   `url`: The company's website.
        *   `priority`: As provided or defaulted.
        *   `relationship-stage`: Default to `prospect`.
        *   `stage`: Keep in sync with `relationship-stage` for backward compatibility while older workflows still reference it.
        *   `source`: Default to `manual` unless the account is created from a clearer origin such as `lead-conversion`.
        *   `source-ref`: Optional provenance link, especially when the Account is created from lead conversion or discovery review.
        *   `date-created`: Current date (YYYY-MM-DD).
        *   `date-modified`: Current date (YYYY-MM-DD).
    *   **Body Sections:**
        *   Populate all sections defined in `templates/account-template.md` (Executive Summary, Financial Architecture, etc.) with synthesized information from the research.
        *   Create financial tables if data is available (retaining local currency but providing USD conversions).
        *   Create competitive comparison tables.

5.  **File Creation:**
    *   Write the generated content to `CRM_DATA_PATH/Accounts/[Company-Name].md`.

6.  **Compatibility Note:**
    *   `relationship-stage` is the clearer v4 relationship-state field.
    *   `stage` should still be populated in parallel until older repo logic is fully migrated.

7.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add Accounts/[Company-Name].md && git commit -m "agent: created account [Company-Name]"
        ```
    *   Run `update-dashboard` to reflect the new account.

8.  **Output:**
    *   Confirm the file creation to the user and display the path.
