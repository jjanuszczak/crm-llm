# Skill: CRM Opportunity Manager

## Description
Manages the lifecycle of active commercial work in the CRM. Use this skill when the user wants to create, structure, advance, review, or close an `Opportunity`, or when they want to decide what should exist next around an active opportunity.

This skill treats `Opportunity` as the operational center of gravity for pre-close commercial work. It owns the workflow question:

- "What should exist, change, or happen next for this opportunity?"

Current implementation support covers:
- canonical opportunity creation
- structural updates to parent context and core metadata
- stakeholder and influencer assignment
- stage and probability updates
- paused opportunity handling for "come back later" workflows
- won/lost close handling
- optional won-to-engagement handoff with first workstream creation
- stale archive handling
- spawning follow-up `Tasks`, `Activities`, and `Notes`
- read-only opportunity review

## When To Use
- A commercial relationship already exists and an opportunity should be created or refined.
- The user wants to update stage, probability, value, or close timing.
- The user wants to pause an opportunity without marking it lost.
- The user wants to assign a primary contact or influencer set.
- The user wants to create follow-up operational records from opportunity context.
- The user wants to mark an opportunity won, lost, or stale.
- The user wants to convert a won opportunity into a post-close engagement.
- The user wants a concise review of what is missing or what should happen next.

## Workflow

1. **Orient to the relationship**
   - Read `crm-data/index.md` first when locating the opportunity cluster.
   - Read the target `Opportunity`, linked `Account`, `Organization`, and `Contact`.
   - Check linked `Tasks`, `Activities`, and `Notes` when execution context matters.
   - Read `crm-data/log.md` when recent mutation history may affect the decision.

2. **Choose the right motion**
   - `create`
   - `update`
   - `assign-stakeholders`
   - `set-stage`
   - `set-probability`
   - `mark-won`
   - `mark-lost`
   - `archive-stale`
   - `spawn-task`
   - `spawn-activity`
   - `spawn-note`
   - `review`

3. **Validate parent context**
   - Resolve `Account` first.
   - Resolve `Organization` from the account unless the user explicitly overrides it.
   - Resolve `Primary Contact`.
   - Carry `Lead` or `Deal` provenance when it exists.

4. **Preserve repo policy**
   - Filenames must stay hyphen-safe.
   - Use canonical opportunity fields from `docs/schema-spec.md`.
   - Mutation workflows must update `crm-data/index.md` and append `crm-data/log.md`.
   - Prefer workflow-level judgment, not ad hoc frontmatter edits.

5. **Respect the pre-close boundary**
   - `Opportunity` is the pre-close pursuit record.
   - Once work is truly won, prefer creating an `Engagement`.
   - If the opportunity is marked `closed-won` but no engagement exists yet, treat that as a handoff gap.

## User-Facing Usage

The user can ask for:
- "Create an opportunity for Example Company."
- "Advance this opportunity to proposal at 40%."
- "Pause this opportunity until next quarter."
- "Add two influencers."
- "Mark this opportunity lost and capture the reason."
- "Mark this opportunity won and create the engagement."
- "Create the follow-up task and the meeting activity."
- "Review this opportunity and tell me what is missing."

Prefer the current CLI for supported flows:
- `python3 scripts/opportunity_manager.py create ...`
- `python3 scripts/opportunity_manager.py update ...`
- `python3 scripts/opportunity_manager.py assign-stakeholders ...`
- `python3 scripts/opportunity_manager.py set-stage ...`
- `python3 scripts/opportunity_manager.py set-probability ...`
- `python3 scripts/opportunity_manager.py mark-won ...`
- `python3 scripts/opportunity_manager.py mark-lost ...`
- `python3 scripts/opportunity_manager.py archive-stale ...`
- `python3 scripts/opportunity_manager.py spawn-task ...`
- `python3 scripts/opportunity_manager.py spawn-activity ...`
- `python3 scripts/opportunity_manager.py spawn-note ...`
- `python3 scripts/opportunity_manager.py review ...`

## References
- Read [references/lifecycle.md](references/lifecycle.md) for the working opportunity state model.
- Read [references/cli-patterns.md](references/cli-patterns.md) for command shapes.
- Read [references/close-rules.md](references/close-rules.md) for won/lost/stale handling rules.
- Read [references/stakeholder-model.md](references/stakeholder-model.md) for stakeholder expectations.

## Current Implementation Notes
- The canonical implementation is [scripts/opportunity_manager.py](scripts/opportunity_manager.py).
- The compatibility wrapper remains at [../../../../scripts/opportunity_manager.py](../../../../scripts/opportunity_manager.py).
- This skill complements `crm-lead-manager`; it does not replace lead qualification or conversion policy.
- For post-close execution structure, it should hand off into `crm-engagement-manager`, not absorb engagement lifecycle logic wholesale.
