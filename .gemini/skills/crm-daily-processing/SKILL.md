# Skill: CRM Daily Processing

## Description
Runs the standard daily CRM operating loop for a live vault with the principal operator kept in the loop. This skill is the top-level workflow for starting the day, reconciling new Workspace signals, collecting off-system updates from the user, reviewing tasks and opportunities, and refreshing the relationship views.

## Usage
`crm-daily-processing`

Use this skill when the user wants to:
- start the day in the CRM
- run the normal daily operating loop
- reconcile new Gmail / Calendar activity with live opportunities and tasks
- optionally reconcile Granola meeting notes when Granola MCP is available
- review overdue or waiting work
- capture updates that happened outside Google Workspace or outside the CRM

Do not use this skill for one-off record creation when a narrower skill is clearly sufficient.

## Workflow

1. **Orient First**
   * Read `CRM_DATA_PATH/DASHBOARD.md`, `CRM_DATA_PATH/index.md`, and `CRM_DATA_PATH/log.md` if present.
   * Form a quick view of:
     * urgent `todo` work
     * `waiting` items coming due for review
     * hot relationships or opportunities that need explicit judgment

2. **Run Workspace Intake**
   * Run the canonical Workspace ingest flow via `crm-ingest-gws`.
   * Review staged files in `CRM_DATA_PATH/staging/`, especially:
     * `activity_updates.json`
     * `contact_discoveries.json`
     * `lead_decisions.json`
     * `opportunity_suggestions.json`
     * `task_suggestions.json`
     * `drive_document_updates.json` when CRM-labeled Google Docs were considered by the ingester
   * Treat ingest as proposal generation, not automatic truth.

3. **Optionally Pull Granola Context**
   * If Granola MCP is connected in the current AI client, query Granola for recent meetings that may not be visible through the current Gmail / Calendar / Google Drive path.
   * Focus on:
     * recent meetings with known CRM contacts, accounts, organizations, or opportunities
     * action items or next steps not already reflected in `task_suggestions.json`
     * strategic notes or decisions that would materially improve relationship memory
   * Treat Granola as an optional enrichment layer, not a required dependency.
   * If Granola MCP is not connected or returns no useful results, continue the workflow without blocking.

4. **Process Staged Signals**
   * Apply clear, low-ambiguity updates directly.
   * For judgment-heavy items, summarize the proposed change and confirm it with the user before mutating key records.
   * Prefer enriching existing `Activities`, `Tasks`, `Leads`, and `Opportunities` over creating duplicates.
   * If Granola surfaced useful meeting content, convert it into durable CRM changes as `Activities`, `Notes`, or `Task` updates with clear provenance.

5. **Ask For Off-System Updates**
   * Ask the user concise questions about important changes not visible in Gmail / Calendar.
   * Typical prompts:
     * what happened on WhatsApp / Signal / in person?
     * what tasks are actually done, blocked, or waiting?
     * what opportunities changed stage, momentum, or commercial reality?
   * When Granola is available, treat it as a partial substitute for manual recall of meeting details, but still ask for anything that happened outside captured systems.
   * Convert user-provided updates into durable CRM changes, usually as `Activities`, task updates, lead-stage changes, or opportunity-stage updates.

6. **Review Task Queue**
   * Review overdue `todo` tasks first.
   * Review `waiting` tasks as reminder-driven review points, not execution failures.
   * Normalize task states:
     * `todo` when you owe the next move
     * `waiting` when someone else owes the next move
     * `completed` when the task was done or clearly superseded
   * When moving a task to `waiting`, reset `due-date` to the next review date.

7. **Review Opportunity And Lead Status**
   * Check whether any live opportunities should change stage, probability, or next-step framing.
   * Check whether active leads should stay leads, advance in lead status, or convert.
   * Use `crm-lead-manager` and `crm-opportunity-manager` when lifecycle updates are substantive.

8. **Execute Immediate Follow-Through**
   * Draft or send the obvious follow-up emails the user asks for.
   * Log meaningful outbound and inbound interactions as `Activities`.
   * Create or update `Tasks` so the next move is explicit.

9. **Refresh Derived Views**
   * Run `update-dashboard`.
   * Rebuild `index.md` if needed.
   * Ensure `log.md` reflects meaningful mutations performed during the session.

10. **Close With A Daily Summary**
   * Give the user a concise report:
     * what was ingested
     * what was updated
     * what remains urgent
     * what is now waiting on others
   * If requested, use `crm-create-daily-report` to write a formal session report.

## Human-In-The-Loop Rules

- Do not silently make judgment-heavy commercial decisions when the evidence is ambiguous.
- Ask the user before:
  * creating a new opportunity from weak signal
  * converting a lead
  * closing a meaningful opportunity as lost
  * changing the commercial interpretation of a relationship
- It is fine to act directly on obvious hygiene items such as:
  * completing clearly finished tasks
  * moving follow-up tasks to `waiting` after an email is sent
  * logging already-sent emails or completed meetings

## Output Standard

A good run of this skill should leave the vault with:
- current Gmail / Calendar ingest state
- optional Granola meeting context reviewed when available
- staged proposals reviewed or explicitly deferred
- user-provided off-system updates captured
- task states reconciled
- opportunities and leads updated where needed
- refreshed dashboard / index / log
- a concise end-of-run summary for the user

## Supporting Skills

Use these as sub-workflows when needed:
- `crm-ingest-gws`
- `update-dashboard`
- `crm-lead-manager`
- `crm-opportunity-manager`
- `crm-create-activity`
- `crm-create-task`
- `crm-create-note`
- `crm-create-lead`
- `crm-create-opportunity`
- `crm-create-daily-report`

## Granola Guidance

- Granola MCP is an optional interactive tool source, not part of the repo's guaranteed baseline.
- If connected, use it after the main Workspace ingest so the existing Gmail / Calendar / Drive logic runs first.
- Prefer Granola for:
  * meeting action items that were not explicit in email
  * meeting summaries or decisions that improve CRM memory quality
  * validating whether a meeting-derived task or activity should exist
- Do not assume every meeting exists in Granola, and do not block the daily loop on Granola availability.
