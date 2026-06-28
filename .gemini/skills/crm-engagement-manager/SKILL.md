# Skill: CRM Engagement Manager

## Description
Manages the lifecycle of post-close commercial work in the CRM. Use this skill when the user wants to create, structure, update, review, pause, complete, or cancel an `Engagement`, or when they want to decide what commercially won work should exist after an `Opportunity` is closed or a pilot is agreed.

This skill owns the workflow question:

- "What commercially won work exists, and how should it be structured?"

It also owns the boundary between:
- pre-close `Opportunity`
- post-close `Engagement`
- child `Workstream`

## When To Use
- An `Opportunity` has been won and should become an `Engagement`.
- A pilot or paid diagnostic should be represented as commercially active work.
- The user wants to create, update, or review an engagement.
- The user wants to add or reorganize workstreams under an engagement.
- The user wants to pause, complete, or cancel an engagement.
- The user wants to understand whether current work belongs in `Opportunity` or `Engagement`.

## Workflow

1. **Orient to the commercial context**
   - Read `crm-data/index.md` first when locating the relationship cluster.
   - Read the relevant `Opportunity`, `Account`, `Organization`, and `Contact`.
   - Read linked `Tasks`, `Activities`, and `Notes` when execution context matters.
   - Read `crm-data/log.md` when recent mutation history may affect the decision.

2. **Choose the right motion**
   - `create`
   - `update`
   - `review`
   - `mark-active`
   - `pause`
   - `complete`
   - `cancel`
   - `create-workstream`
   - `re-scope-workstream`
   - `link-opportunity`

3. **Preserve model boundaries**
   - Keep unpaid or ambiguous pre-close work on the `Opportunity`.
   - Create an `Engagement` only when there is a real commercial commitment.
   - Require each `Workstream` to belong to exactly one `Engagement`.
   - Keep the relationship-first model intact.

4. **Preserve repo policy**
   - Use canonical fields from `docs/schema-spec.md`.
   - Mutation workflows must update `crm-data/index.md` and append `crm-data/log.md`.
   - Prefer workflow-level judgment, not ad hoc frontmatter edits.

## User-Facing Usage

The user can ask for:
- "Convert this won opportunity into an engagement."
- "Create an engagement for this pilot."
- "Add a research workstream under this client engagement."
- "Pause this engagement until contract terms are resolved."
- "Review this engagement and tell me what is missing."

## Planned Implementation Surface

Expected canonical implementation:
- `.gemini/skills/crm-engagement-manager/scripts/engagement_manager.py`

Supporting creation skills:
- `crm-create-engagement`
- `crm-create-workstream`

## Current Implementation Notes
- The canonical implementation is `.gemini/skills/crm-engagement-manager/scripts/engagement_manager.py`.
- The compatibility wrapper is `scripts/engagement_manager.py`.
- Current implementation support covers:
  - engagement creation
  - engagement update
  - engagement status changes
  - source-opportunity linking
  - workstream creation
  - workstream update
  - read-only engagement review
