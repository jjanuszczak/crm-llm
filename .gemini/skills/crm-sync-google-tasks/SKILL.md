---
name: crm-sync-google-tasks
description: Reconcile CRM task completion state with Google Tasks in a narrow, review-aware utility workflow while keeping the local vault as the source of truth.
---

# CRM Sync Google Tasks

## Overview

This skill is a narrow utility for reconciling CRM tasks with Google Tasks.

It is not a top-level operating loop. The primary workflows in the current repo are:
- `crm-daily-processing` for the daily operator loop
- `crm-ingest-gws` for Gmail and Calendar intake
- `crm-create-task` and `task_manager.py` for authoritative task writes

Use this skill only when Google Tasks is actively part of the user’s personal execution system and the goal is to keep completion state reasonably aligned with the CRM.

The local CRM vault remains the source of truth.
Each synced CRM task should persist:
- `google-task-id`
- `google-task-list-id`

## Current Status

The legacy script still exists:

```bash
python3 .gemini/skills/crm-sync-google-tasks/scripts/sync-tasks.py
```

But it should be treated as a compatibility utility, not a fully modernized writer. Its current limitations matter:
- older records may still need one-time ID backfill by matching on title
- it should not be trusted for nuanced task-state interpretation
- it is primarily for mirroring CRM task state into Google Tasks while allowing remote completion to flow back

Because of those limits, this skill should be run with explicit review in mind.

## When To Use

Use this skill when you need to:
- ensure CRM tasks have durable Google Task identities
- reflect CRM task state into Google Tasks for personal task visibility
- pull clear remote completion signals back into the CRM
- keep Google Task title, due date, and completion state aligned to the CRM

Do not use this skill as the primary way to manage CRM tasks.

Do not use this skill to decide relationship workflow state such as:
- whether a task should be `waiting`
- whether a task is blocked or superseded
- whether a new follow-up task should exist at all

Those decisions belong in the CRM task workflow, usually through `crm-daily-processing`, `crm-create-task`, or direct use of [task_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/task_manager.py).

## Operating Model

### 1. Resolve local task context

- Read `CRM_DATA_PATH` from `.env` or the environment.
- Scan `CRM_DATA_PATH/Tasks/` for current task records.
- Treat local CRM records as authoritative for:
  - task naming
  - due dates
  - parent context
  - final task-state meaning

### 2. Read Google Tasks carefully

- Use `gws` to read the target Google Tasks list.
- Include completed tasks when reconciling.
- Treat Google Tasks as an execution surface, not as the canonical CRM system of record.

### 3. Restrict sync semantics

This skill should operate conservatively:
- each local CRM task should have a Google counterpart and persisted Google identifiers
- local title and due date should patch the Google task on subsequent sync runs
- local `completed` should patch the Google task to `completed`
- remotely completed tasks may be marked `completed` locally

Do not automatically reinterpret:
- `waiting`
- `blocked`
- `in-progress`
- relationship-parent changes
- opportunity or lead linkage

In current repo terms:
- `todo` means John owes the next move
- `waiting` means someone else owes the next move and the local due date is the next review date
- `completed` means done or clearly superseded

`waiting` remains a local CRM semantic even if the mirrored Google task stays open.

### 4. Use canonical local writers

If the sync updates a local task, it should go through current mutation pathways rather than raw regex rewrites whenever possible.

That means preferring:
- [task_manager.py](/Users/johnjanuszczak/Projects/crm-logic/scripts/task_manager.py) for local task status updates
- repo-standard mutation logging behavior
- downstream refresh of `index.md` and derived views when local writes occurred

### 5. Rebuild navigation and summaries after local mutation

If any local CRM task changed:
- rebuild `crm-data/index.md`
- append the appropriate mutation history to `crm-data/log.md` through the task writer path
- refresh dashboard and derived task views if the wider workflow did not already do that

Do not auto-commit changes. Git actions are a separate operator decision.

## Safe Review Rules

Before applying local updates, check for these red flags:
- duplicate remote tasks with the same title
- old local task titles that no longer reflect the real work item
- local task status outside the current normalized model
- stale tasks whose next correct action is actually `waiting` review, not completion

If any of those are present, review before mutating the vault.

## Recommended Usage Pattern

1. Review overdue and `waiting` work in the CRM first.
2. Normalize task meaning locally.
3. Run the Google Tasks reconciliation utility.
4. Review any ambiguous matches.
5. Refresh dashboard / index / log if local writes occurred.

This ordering avoids letting a lightweight external task surface distort the CRM’s task semantics.

## Output Standard

A good run of this skill should report:
- how many local tasks were linked or backfilled with Google identifiers
- how many local tasks were created in Google Tasks
- how many local tasks were marked `completed` from clear remote completion
- how many remote tasks were updated from local CRM state
- whether local index / dashboard refresh was run
- any ambiguous title collisions that were intentionally left unresolved

## Supporting Skills

Use these as adjacent or follow-on workflows:
- `crm-daily-processing`
- `crm-create-task`
- `update-dashboard`
