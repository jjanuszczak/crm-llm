# Skill: Create Account

## Description
Creates a new account file in the `Accounts/` directory for a specified company. This skill automates the file creation, populates the YAML frontmatter with provided details, and performs web research to generate a comprehensive "Strategic Due Diligence Report" based on the `Templates/account-template.md`.

## Usage
`create-account "Company Name" --url "https://example.com" --priority "medium"`

## Arguments
*   `company` (Required): The full name of the company (e.g., "Example Bank").
*   `url` (Optional): The company's official website URL.
*   `priority` (Optional): The priority level for this account (`high`, `medium`, `low`). Defaults to `medium`.

## Implementation Steps

1.  **File Naming:**
    *   Convert the `company` to `[Company-Name].md` format (e.g., `ZingHR.md`).
    *   Check if `Accounts/[Company-Name].md` already exists. If it does, stop and notify the user.

2.  **Web Research:**
    *   **Search 1:** Google search for `"[Company Name]" headquarters industry revenue headcount 2025 2026` to find frontmatter data.
    *   **Search 2:** Google search for `"[Company Name]" strategic due diligence report news 2025 2026` to find recent business developments.
    *   **Search 3:** Google search for `"[Company Name]" leadership founders funding investors` to find structural information.
    *   **Search 4:** Google search for `"[Company Name]" competitors Gartner Peer Insights G2 reviews` to find market positioning.

3.  **Content Generation (Using `Templates/account-template.md`):**
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

4.  **File Creation:**
    *   Write the generated content to `Accounts/[Company-Name].md`.

5.  **Output:**
    *   Confirm the file creation to the user and display the path.
