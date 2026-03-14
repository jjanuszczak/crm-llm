# Skill: Create Note

## Description
Creates a first-class `Note` record in `CRM_DATA_PATH/Notes/` using the v4 note model. Notes represent durable context, research, interpretation, or strategic memory and use one primary parent plus optional secondary links.

## Usage
`create-note --title "Jane relationship context" --primary-parent-type contact --primary-parent "Contacts/Jane-Doe" --secondary-links "Accounts/Example-Capital"`

## Implementation Steps

1. **Dynamic Path Resolution:**
   * Read `CRM_DATA_PATH` from `.env`.
   * Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2. **Creation:**
   * Create records in `CRM_DATA_PATH/Notes/` using `templates/note-template.md`.
   * Require:
     * `title`
     * `primary-parent-type`
     * `primary-parent`
   * Allow optional `secondary-links`, `source`, and `source-ref`.

3. **Linking Rules:**
   * Use one primary parent plus optional secondary links.
   * Expected primary parent precedence in the broader system is:
     * `Opportunity`
     * `Contact`
     * `Account`

4. **Behavior:**
   * Notes may exist without a corresponding `Activity` when they are not tied to a discrete event.
   * Notes should remain durable context, not raw inbox items.

5. **Output:**
   * Confirm the created note path to the user.
