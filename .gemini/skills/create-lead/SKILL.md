# Skill: Create Lead

## Description
Creates and manages first-class `Lead` records in `CRM_DATA_PATH/Leads/` using the v4 lead model. This skill supports sparse early leads, lifecycle status transitions, qualification readiness checks, and revival from `disqualified`.

## Usage
- `create-lead --name "Jane Doe - Example Capital" --person-name "Jane Doe" --company-name "Example Capital" --email "jane@example.com" --lead-source "gmail"`
- `lead-set-status "Jane-Doe-Example-Capital" --status engaged`
- `lead-revive "Jane-Doe-Example-Capital" --meaningful-two-way`
- `lead-validate-qualified "Jane-Doe-Example-Capital"`
- `lead-convert "Jane-Doe-Example-Capital" --opportunity-name "Example Capital - Strategic Advisory - 2026"`

## Implementation Steps

1. **Dynamic Path Resolution:**
   * Read `CRM_DATA_PATH` from `.env`.
   * Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2. **Creation:**
   * Create records in `CRM_DATA_PATH/Leads/` using `templates/lead-template.md`.
   * Allow sparse early leads with any one of `person-name`, `company-name`, or `email`.
   * Populate `lead-source`, `owner`, `date-created`, and `date-modified`.

3. **Lifecycle Rules:**
   * Support statuses:
     * `new`
     * `prospect`
     * `engaged`
     * `qualified`
     * `disqualified`
   * Enforce allowed transitions between statuses.
   * Conversion creates:
     * `Organization`
     * `Contact`
     * `Account`
     * `Opportunity`
   * Archive converted leads to `CRM_DATA_PATH/Leads/Converted/`.

4. **Qualification Validation:**
   * Before a lead can move to `qualified`, require both:
     * `person-name`
     * `company-name`

5. **Revival:**
   * Allow `disqualified` leads to be revived.
   * Revive to `engaged` when meaningful two-way communication is present.
   * Otherwise revive to `prospect`.

6. **Conversion Carry-Forward:**
   * Copy any lead-linked v4 `Note` and `Activity` records onto the new `Opportunity`, with secondary links to the new `Contact` and `Account`.
   * Move any open lead-linked tasks primarily onto the new `Opportunity`.
   * Preserve provenance back to the source `Lead`.
   * Link the new `Account` to the new canonical `Organization`.

7. **Output:**
   * Confirm the affected lead path and resulting status to the user.
