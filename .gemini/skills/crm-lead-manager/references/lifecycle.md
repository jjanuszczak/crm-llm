# Lead Lifecycle Reference

## Purpose
This reference defines the intended lead lifecycle and conversion outcomes for the CRM.

## Stage Definitions

### `new`
- A person, organization, or both have been identified.
- There is not yet meaningful engagement.
- Typical examples:
  - referred but not contacted
  - discovered through research
  - seen in inbox or staging but not yet worked

### `prospect`
- There is enough signal to keep the lead visible.
- There is not yet enough relationship evidence to treat it as actively engaged.
- Typical examples:
  - likely relevant but only lightly researched
  - known through a weak referral
  - worth monitoring before outreach

### `engaged`
- There is a known contact.
- There has been real interaction, such as:
  - email sent or received
  - meeting held or scheduled
  - call completed
  - other meaningful activity

This is stronger than "we know about them." It means the relationship is active enough to justify operating attention.

### `qualified`
- Contact and organization are both known.
- There is a credible reason to pursue a structured working relationship.
- Qualification means "worth pursuing toward a durable CRM shape."
- It does not necessarily mean there is already a fully defined commercial opportunity, only that the lead is ready to be worked with intentionally.

### `deferred`
- The lead remains viable, but active work should pause until a later review point.
- Use this when the answer is "not now" rather than "no."
- Pair `deferred` with an open `Task` using `status: waiting` and a future `due-date` so the review is reminder-driven.
- Do not use `disqualified` unless the relationship is no longer worth pursuing based on current evidence.

### `converted`
- The lead has been resolved into durable CRM records.
- Conversion should happen only when the target operating model is clear.

### `disqualified`
- The lead is not viable based on current evidence.
- Disqualification should preserve the record and rationale, because future revival may still happen.

## Conversion Outcomes

### 1. Commercial Opportunity Path
Use when the goal is active commercial work.

Create:
- `Organization`
- `Contact`
- `Account`
- `Opportunity`

This is implemented in [../scripts/lead_manager.py](../scripts/lead_manager.py).

### 2. Relationship-Only Path
Use when the lead is important but does not represent an active commercial opportunity.

Typical examples:
- supplier
- partner
- strategic relationship
- deal-related contact where no current account/opportunity should exist

Create:
- `Organization`
- `Contact`

Do not create:
- `Account` unless a commercial relationship wrapper is actually needed
- `Opportunity` unless active work exists

This is now implemented in [../scripts/lead_manager.py](../scripts/lead_manager.py).

## Operating Heuristics
- If active work exists, the center of gravity should usually become an `Opportunity`.
- If stable identity matters but there is no active commercial workflow, prefer `Organization + Contact`.
- Do not create `Account` or `Opportunity` just because the lead is qualified.
- Qualification is about relationship intent and readiness, not forced commercial modeling.
- Use `deferred` when the lead is still potentially valuable but timing, readiness, or external dependency makes immediate action inappropriate.
