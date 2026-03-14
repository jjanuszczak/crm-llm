# Skill: Create Inbox Item

## Description
Creates and processes first-class `Inbox` items in `CRM_DATA_PATH/Inbox/`. This replaces the old notes-as-inbox workflow. Inbox items are temporary raw captures that can be processed into durable records such as `Note`, `Activity`, `Task`, or `Lead`.

## Usage
- `create-inbox-item --title "Raw notes from Jane meeting" --content "..." --source manual`
- `process-inbox-item "Raw-notes-from-Jane-meeting" --outputs note activity --primary-parent-type opportunity --primary-parent "Opportunities/Example-Capital-Strategic-Advisory-2026"`

## Implementation Steps

1. **Dynamic Path Resolution:**
   * Read `CRM_DATA_PATH` from `.env`.
   * Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2. **Creation:**
   * Create records in `CRM_DATA_PATH/Inbox/` using `templates/inbox-template.md`.
   * Populate `id`, `title`, `status`, `owner`, `source`, `source-ref`, `captured-at`, `date-created`, and `date-modified`.

3. **Processing:**
   * Allow one Inbox item to produce multiple outputs in one pass.
   * Supported initial outputs:
     * `Note`
     * `Activity`
     * `Task`
     * `Lead`
   * Require a primary parent when creating `Note` or `Activity`.

4. **Lifecycle Rules:**
   * Inbox items are temporary by default.
   * Processed items should either be marked `processed` or deleted from the active queue.
   * If the source is event-based, create an `Activity` during processing.

5. **Output:**
   * Confirm the processed Inbox item path and the durable record paths created from it.
