# Skill: Matchmaker

## Description
Runs the brokerage matchmaker to identify likely matches between `Deals` / `Deal-Flow` inventory and investor `Accounts`, then stages the results in `CRM_DATA_PATH/staging/matches.json`.

## Usage
`matchmaker`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **Load Inventory:**
    *   Scan the canonical `CRM_DATA_PATH/Deals/` directory for markdown deal files.
    *   If a legacy vault still uses `Deal-Flow/`, fall back to that path for compatibility.
    *   Parse frontmatter for sector, fundraising stage, and raise information.

3.  **Load Investor Accounts:**
    *   Scan `CRM_DATA_PATH/Accounts/` for markdown account files.
    *   Resolve the linked `Organization` when present.
    *   Filter for investor organizations/accounts.
    *   Parse mandate and check-size fields from the Organization layer with Account fallback for legacy records.

4.  **Calculate Matches:**
    *   Score sector alignment between the deal and the investor mandate.
    *   Add supporting signal from raise-size and stage heuristics.
    *   Keep only high-confidence matches.

5.  **Write Output:**
    *   Save results to `CRM_DATA_PATH/staging/matches.json`.

6.  **Output:**
    *   Confirm how many high-probability matches were staged.
