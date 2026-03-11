# Skill: Create Account

## Description
Creates a new account file in the `CRM_DATA_PATH/Accounts/` directory for a specified company. This skill automates the file creation, populates the YAML frontmatter with provided details, and performs web research to generate a comprehensive "Strategic Due Diligence Report" based on the `Templates/account-template.md`.

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

4.  **Content Generation (Using `Templates/account-template.md`):**
    *   **Frontmatter:**
        *   `company-name`: The official name of the company.
        *   `headquarters`: City, Country.
        *   `industry`: Primary industry sector.
        *   `size`: Revenue in USD Millions (converted from local currency if necessary) or Headcount.
        *   `url`: The company's website.
        *   `priority`: As provided or defaulted.
        *   `stage`: Default to `prospect`.
        *   `date-created`: Current date (YYYY-MM-DD).
        *   `date-modified`: Current date (YYYY-MM-DD).
    *   **Body Sections:**
        *   Populate all sections defined in `Templates/account-template.md` (Executive Summary, Financial Architecture, etc.) with synthesized information from the research.
        *   Create financial tables if data is available (retaining local currency but providing USD conversions).
        *   Create competitive comparison tables.

5.  **File Creation:**
    *   Write the generated content to `CRM_DATA_PATH/Accounts/[Company-Name].md`.

6.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add Accounts/[Company-Name].md && git commit -m "agent: created account [Company-Name]"
        ```
    *   Run `update-dashboard` to reflect the new account.

7.  **Output:**
    *   Confirm the file creation to the user and display the path.
