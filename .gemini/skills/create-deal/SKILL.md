# Skill: Create Deal

## Description
Captures a new startup into the `CRM_DATA_PATH/Deals/` inventory. This skill automates the synthesis of information from Google Drive, Gmail, the company's website, and targeted web research to create a comprehensive investment profile using the `templates/deal-template.md`. It also identifies and creates contact profiles for founders and links the deal to active opportunities if a target client is identified.

## Usage
`create-deal "Startup Name" --url "https://startup.com" --target-client "[[Account Name]]"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **Multi-Source Research:**
    *   **Google Drive:** Search for a folder named `[Startup Name]`. Read the "Pitch Deck" or "Backgrounder" documents found within.
    *   **Gmail:** Search for emails from the `[startup.com]` domain to extract recent updates, traction metrics, and founder names.
    *   **Website:** Fetch the provided `url`. Analyze the landing page for the core value proposition and product tiers.
    *   **Web Research:** Google search for `"[Startup Name]" funding news founders 2025 2026` to find recent developments, awards, or leadership changes not in Drive or Gmail.

3.  **Entity Creation (Founders):**
    *   Identify founders from the research.
    *   For each founder, run the `create-contact` skill to establish their profile in `CRM_DATA_PATH/Contacts/`.

4.  **Deal-Flow Entry (Using `templates/deal-template.md`):**
    *   **Frontmatter:** Populate `startup-name`, `sector`, `stage`, and `location`. Set `google-drive-url` to the URL of the folder found in Step 1. Set `date-sourced` and `date-modified` to the current date.
    *   **Body:** Synthesize the "Executive Summary," "Problem & Solution," and "Investment Highlights" based on the research.
    *   **Due Diligence:** Mark "Pitch Deck Reviewed" and "Tech/Product Demo" as checked if the corresponding sources were analyzed.
    *   **Brokerage Strategy:** Link the `target-client` if provided.

5.  **Opportunity Linking (Optional):**
    *   If a `target-client` is provided, run the `create-opportunity` skill to create a referral opportunity in `CRM_DATA_PATH/Opportunities/` (e.g., "[[Account Name]] - [[Startup Name]] Deal Flow - [YYYY]").

6.  **File Creation & Dashboard:**
    *   Write the deal entry to `CRM_DATA_PATH/Deals/[Startup-Name].md`.

7.  **Automatic Bookkeeping:**
    *   Commit the new file to the nested data repository:
        ```bash
        cd $CRM_DATA_PATH && git add "Deals/[Startup-Name].md" && git commit -m "agent: added deal [Startup-Name]"
        ```
    *   Run `update-dashboard`.

8.  **Output:**
    *   Confirm the creation of the deal, contacts, and opportunity to the user.
