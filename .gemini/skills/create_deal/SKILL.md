# Skill: Create Deal

## Description
Captures a new startup into the `Deal-Flow/` inventory. This skill automates the synthesis of information from Google Drive, Gmail, the company's website, and targeted web research to create a comprehensive investment profile using the `Templates/deal-template.md`. It also identifies and creates contact profiles for founders and links the deal to active opportunities if a target client is identified.

## Usage
`create-deal "Startup Name" --url "https://startup.com" --target-client "[[Account Name]]"`

## Arguments
*   `startup` (Required): The full name of the startup (e.g., "Flatpeak").
*   `url` (Optional): The startup's official website URL.
*   `target-client` (Optional): A client account interested in this type of deal flow (e.g., "[[1882 Energy Ventures]]").

## Implementation Steps

1.  **Multi-Source Research:**
    *   **Google Drive:** Search for a folder named `[Startup Name]`. Read the "Pitch Deck" or "Backgrounder" documents found within.
    *   **Gmail:** Search for emails from the `[startup.com]` domain to extract recent updates, traction metrics, and founder names.
    *   **Website:** Fetch the provided `url`. Analyze the landing page for the core value proposition and product tiers.
    *   **Web Research:** Google search for `"[Startup Name]" funding news founders 2025 2026` to find recent developments, awards, or leadership changes not in Drive or Gmail.

2.  **Entity Creation (Founders):**
    *   Identify founders from the research.
    *   For each founder, run the `create_contact` skill to establish their profile in `Contacts/`.

3.  **Deal-Flow Entry (Using `Templates/deal-template.md`):**
    *   **Frontmatter:** Populate `startup-name`, `sector`, `stage`, and `location`. Set `google-drive-url` to the URL of the folder found in Step 1. Set `date-sourced` and `date-modified` to the current date.
    *   **Body:** Synthesize the "Executive Summary," "Problem & Solution," and "Investment Highlights" based on the research.
    *   **Due Diligence:** Mark "Pitch Deck Reviewed" and "Tech/Product Demo" as checked if the corresponding sources were analyzed.
    *   **Brokerage Strategy:** Link the `target-client` if provided.

4.  **Opportunity Linking (Optional):**
    *   If a `target-client` is provided, run the `create_opportunity` skill to create a referral opportunity in `Opportunities/` (e.g., "[[Account Name]] - [[Startup Name]] Deal Flow - [YYYY]").

5.  **File Creation & Dashboard:**
    *   Write the deal entry to `Deal-Flow/[Startup-Name].md`.
    *   Run `update_dashboard`.

6.  **Output:**
    *   Confirm the creation of the deal, contacts, and opportunity to the user.
