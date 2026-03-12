# Skill: Sync Workspace

## Description
Proactively scans Gmail and Google Calendar for interactions with contacts linked to active opportunities. Infers updates to opportunity stages, activity logs, and task statuses.

## Usage
`sync-workspace [--since "YYYY-MM-DD"] [--autonomous]`

## Implementation Steps

1.  **Mode Initialization:**
    *   **Autonomous Mode:** If the `--autonomous` flag is present, the agent will execute all high-confidence updates (Activity creation, Task closing, Stage updates) without stopping for confirmation.
    *   **Interactive Mode (Default):** The agent will present each proposed update individually for user approval.

2.  **Dynamic Path Resolution:**
    *   Read `CRM_DATA_PATH` from `.env`.
    *   Verify `CRM_DATA_PATH` is a subdirectory within the project root.

3.  **Identify Active Contacts & Discovery Scope:**
    *   Scan `CRM_DATA_PATH/Opportunities/` for files where `is-active: true`.
    *   Extract linked `primary-contact` and any `influencers`.
    *   Retrieve email addresses for these contacts from the `CRM_DATA_PATH/Contacts/` directory.

4.  **Search Workspace (Dual-Layer):**
    *   **Gmail (Sync):** Search `after:[since_date] (from:email1 OR from:email2 ...)` to sync existing contacts.
    *   **Gmail (Discovery):** Search `after:[since_date] is:unread` or broader `after:[since_date]` to find new interactions.
    *   **Calendar:** List events `timeMin:[since_date]` involving the identified emails and new attendees.

5.  **AI Filtering & Discovery Pipeline:**
    *   **Domain Filtering:** For any new email address, check against `scripts/noise_domains.json`. Ignore if it's a generic, service, or common noise domain.
    *   **Contextual AI Classification:** For candidates that pass domain filtering:
        *   Fetch the last 3 messages from the thread (`gmail.get`).
        *   **LLM Prompt:** "Analyze this email thread. Determine if the sender is a Professional Prospect (Startup Founder, VC, Corporate) or Noise (Marketing, Personal, Logistics). Provide a one-sentence rationale."
        *   **Staging:** If classified as 'Professional', append to `CRM_DATA_PATH/staging/discovery.json`.

6.  **Inference Logic & Deduplication:**
    *   **New Emails:** Propose a new `Activity` (type: email) and summarize the content.
    *   **Calendar Events:** Propose a new `Activity` (type: meeting) and check if it resolves an existing `Task`.
    *   **Stage Shifts:** If the email/meeting content suggests a milestone, propose updating the `Opportunity` stage.
    *   **Deduplication:** Check `CRM_DATA_PATH/Activities/` for existing entries matching the date/contact before proposing.

7.  **Processing (Interactive Mode):**
    *   For each proposed update, use `ask_user` to present the detail.
    *   **User Actions:**
        *   **Approve:** Execute the creation/update.
        *   **Skip:** Do not apply the change.
        *   **Edit:** User provides a "hint" (e.g., "Change the summary to...") which the agent applies before executing.

8.  **Finalization & Linking:**
    *   Run relevant `create-*` skills for approved changes.
    *   **Linking:** Connect action items in activities to new tasks via Wikilinks.
    *   **Automatic Bookkeeping:**
        *   Commit updates to the data repository: `cd $CRM_DATA_PATH && git add . && git commit -m "agent: synced workspace"`
        *   Run `update-dashboard`.
