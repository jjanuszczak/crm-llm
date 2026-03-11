# Skill: Sync Workspace

## Description
Proactively scans Gmail and Google Calendar for interactions with contacts linked to active opportunities. Infers updates to opportunity stages, activity logs, and task statuses.

## Usage
`sync-workspace --since "YYYY-MM-DD"`

## Implementation Steps

1.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

2.  **Identify Active Contacts:**
    *   Scan `CRM_DATA_PATH/Opportunities/` for files where `is-active: true`.
    *   Extract linked `primary-contact` and any `influencers`.
    *   Retrieve email addresses for these contacts from the `CRM_DATA_PATH/Contacts/` directory.

3.  **Search Workspace:**
    *   **Gmail:** Search `after:[since_date] (from:email1 OR from:email2 ...)` to get a list of message IDs. For each message ID, use `gmail.get` with `format: 'raw'` to retrieve the full message content and headers.
    *   **Calendar:** List events `timeMin:[since_date]` involving the identified emails.

4.  **Inference Logic & Deduplication:**
    *   **New Emails:** If an email is found from a contact, propose a new `Activity` (type: email) and summarize the content.
        *   **Deduplication:** Before proposing, check if an activity with the same date and contact already exists in the `CRM_DATA_PATH/Activities/` directory.
        *   **Email Link:** Extract the `Message-ID` from the email headers and construct a link to the email: `https://mail.google.com/mail/u/0/#search/rfc822msgid:<message-id>`. This link should be included in the proposed activity file.
    *   **Calendar Events:** If a meeting occurred, propose a new `Activity` (type: meeting) and check if it resolves an existing `Task`.
        *   **Deduplication:** Before proposing, check if an activity for that meeting already exists.
    *   **Stage Shifts:** If the email/meeting content suggests a milestone (e.g., "proposal sent," "contract signed"), propose updating the `Opportunity` stage.

5.  **Presentation & Confirmation:**
    *   Present a list of "Proposed Updates" to the user. This should include new activities, new tasks, and updates to existing files.
    *   **DO NOT** create or modify files without explicit user approval for each group of changes.

6.  **Finalization & Linking:**
    *   After approval, run the relevant `create-*` skills.
    *   **Linking:** When creating a task that is an action item from an activity, the task file should include a link back to the activity file. The activity file should also be updated to include a link to the newly created task in the corresponding action item.
    *   **Automatic Bookkeeping:**
        *   After all approved changes are applied, commit the updates to the nested data repository:
            ```bash
            cd $CRM_DATA_PATH && git add . && git commit -m "agent: synced workspace with Gmail/Calendar"
            ```
        *   Run `update-dashboard`.
