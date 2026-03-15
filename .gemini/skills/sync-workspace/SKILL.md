# Skill: Sync Workspace

## Description
Proactively scans Gmail and Google Calendar for interactions with contacts linked to active opportunities. It now runs as a real ingestion workflow that updates telemetry, stages discoveries, and either stages or creates activity records depending on mode.

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
    *   **Gmail (Sync):** Search `after:[since_date] (from:email1 OR to:email1 ...)` to sync known active-opportunity contacts.
    *   **Gmail (Discovery):** Review recent messages for unknown professional-looking senders.
    *   **Calendar:** List upcoming/recent primary-calendar events since `timeMin:[since_date]`.

5.  **Filtering & Discovery Pipeline:**
    *   **Domain Filtering:** For any new email address, check against `scripts/noise_domains.json`. Ignore if it's a generic, service, or common noise domain.
    *   **Discovery Staging:** For candidates that pass filtering, append discovery candidates to `CRM_DATA_PATH/staging/discovery.json`.

6.  **Inference Logic & Deduplication:**
    *   **Known Gmail Messages:** In interactive mode, stage activity proposals in `CRM_DATA_PATH/staging/workspace_updates.json`. In autonomous mode, create `Activity` records directly for known active-opportunity contacts.
    *   **Calendar Events:** Apply the same interactive/autonomous branching for matched attendees.
    *   **Content Enrichment:** Always read the Gmail message body or calendar event description/location/attendees before writing an `Activity`. Never create a durable record from subject or title alone.
    *   **Persistent Checkpointing:** Save the last successful Gmail and Calendar sync timestamps in `CRM_DATA_PATH/staging/workspace_sync_state.json`. Use that checkpoint by default on the next run unless the user explicitly passes `--since`.
    *   **Deduplication:** Skip items whose `source-ref` already exists on an `Activity`.
    *   **Telemetry:** Update `CRM_DATA_PATH/staging/interactions.json` with `last_date` and rolling 7-day hit counts.

7.  **Processing (Interactive Mode):**
    *   Use `CRM_DATA_PATH/staging/workspace_updates.json` as the review queue for proposed Gmail/Calendar activities.
    *   Users can review staged proposals before they are turned into durable records.

8.  **Finalization & Linking:**
    *   Run `python3 .gemini/skills/sync-workspace/scripts/sync-workspace.py [--since YYYY-MM-DD] [--autonomous]`.
    *   Follow with `update-dashboard` after approved or autonomous changes are applied.
