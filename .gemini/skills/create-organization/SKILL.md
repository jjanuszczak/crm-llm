# Skill: Create Organization

## Description
Creates a new organization file in the `CRM_DATA_PATH/Organizations/` directory. Organizations are the stable entity layer for companies, institutions, and other market actors.

## Usage
`create-organization --name "Example Capital" --organization-class investor --url "https://example.com"`

## Implementation Steps

1. **Dynamic Path Resolution:**
   * Read `CRM_DATA_PATH` from `.env`.
   * Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2. **File Naming:**
   * Convert the organization name to `[Organization-Name].md`.
   * Check if `CRM_DATA_PATH/Organizations/[Organization-Name].md` already exists.

3. **Content Generation:**
   * Use `templates/organization-template.md`.
   * Populate stable identity and classification fields.
   * Keep `last-contacted` persisted as an observed signal.
   * Store investor-profile fields such as `investment-mandate` and `check-size` on the Organization when relevant.

4. **Behavior:**
   * Do not store computed execution-priority fields on the Organization.
   * `days-since-contact` should remain computed, not persisted.

5. **Output:**
   * Confirm the created organization path to the user.
