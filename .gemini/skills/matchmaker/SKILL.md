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
    *   Scan `CRM_DATA_PATH/Deal-Flow/` for markdown deal files.
    *   Parse frontmatter for sector, stage, and raise information.

3.  **Load Investor Accounts:**
    *   Scan `CRM_DATA_PATH/Accounts/` for markdown account files.
    *   Filter for `type: investor`.
    *   Parse mandate and check-size fields.

4.  **Calculate Matches:**
    *   Score sector alignment between the deal and the investor mandate.
    *   Add supporting signal from raise-size and stage heuristics.
    *   Keep only high-confidence matches.

5.  **Write Output:**
    *   Save results to `CRM_DATA_PATH/staging/matches.json`.

6.  **Output:**
    *   Confirm how many high-probability matches were staged.
