# CRM Journey Spec

**Status:** Current

This document defines the intended relationship journey from raw lead through closed opportunity and post-close handoff. It complements `docs/schema-spec.md`, which remains the canonical field-level schema reference.

## Purpose

The CRM should show one coherent journey without collapsing different entity lifecycles into the same meaning.

The most important distinction:

- `Lead.status=qualified` means the relationship has enough evidence to convert into durable CRM records.
- `Opportunity.stage=qualified` means a specific commercial or strategic opportunity has been validated enough to pursue as real work.

These are different gates and should stay visually and operationally distinct.

## Canonical Journey

```text
Lead:        new -> prospect -> engaged -> qualified -> converted
                                       \-> deferred
                                       \-> disqualified

Conversion:  qualified Lead -> Organization + Contact + Account + Opportunity

Opportunity: discovery -> qualified -> proposal -> negotiation -> closed-won
                         \-> paused
                         \-> closed-lost

Post-close:  closed-won Opportunity -> Engagement -> one or more Workstreams
```

## Lead Lifecycle

### `new`

An identified person, organization, or both. There is not yet enough evidence to work the relationship actively.

### `prospect`

An identified and plausible lead. There is enough signal to keep it visible, but not enough engagement to treat it as actively worked.

### `engaged`

A real contact exists and there has been meaningful interaction such as an email, call, meeting, referral, or other concrete activity.

### `qualified`

The lead has a known contact, known organization, and credible reason to pursue a structured relationship. This is a conversion-readiness state, not an opportunity sales-stage state.

### `deferred`

The lead is still viable, but active work should pause until a later review point. Use this for "not now" rather than "no."

Deferred leads should usually have an open `Task` with:

- `status: waiting`
- future `due-date`
- `primary-parent-type: lead`
- `primary-parent` pointing to the lead

### `converted`

The lead has been resolved into durable CRM records. Converted leads preserve provenance but should no longer appear as active lead work.

### `disqualified`

The lead is not viable based on current evidence. Use this for a real "no" or wrong-fit outcome, not for delayed timing.

## Opportunity Lifecycle

### `discovery`

A concrete opportunity exists, but the commercial shape, stakeholders, value, timing, or next step still needs discovery.

### `qualified`

The specific opportunity is validated enough to pursue. This means the opportunity itself has sufficient evidence, not merely that the original lead was conversion-ready.

### `proposal`

A proposal, mandate, scope, offer, or concrete commercial path has been presented or is being actively shaped for presentation.

### `negotiation`

Terms, economics, timing, stakeholders, approvals, or final conditions are being worked.

### `paused`

The opportunity is still viable, but active execution is intentionally deferred. Use this for "come back later" when the opportunity should not be closed lost.

Paused opportunities should usually have an open `Task` with:

- `status: waiting`
- future `due-date`
- `primary-parent-type: opportunity`
- `primary-parent` pointing to the opportunity

### `closed-won`

The opportunity succeeded. `is-active` should be `false`.

A closed-won opportunity should usually hand off into:

- `Engagement`
- optionally an initial `Workstream`

The opportunity remains durable commercial history. It should not remain the long-term home for post-close execution tracking.

### `closed-lost`

The opportunity failed, was declined, or is no longer viable. `is-active` should be `false`, and `lost-at-stage`, `lost-reason`, and `lost-date` should be preserved when known.

## Conversion Boundary

Lead conversion is a structural transition, not just a status change.

Default commercial conversion creates or links:

- `Organization`
- `Contact`
- `Account`
- `Opportunity`

Relationship-only conversion creates or links:

- `Organization`
- `Contact`

Use relationship-only conversion when the lead matters as durable relationship memory but does not represent active commercial work.

## Dashboard Journey Columns

A dashboard that visualizes the full journey should avoid a single generic `Qualified` column. Recommended columns are:

```text
New Lead
Prospect
Engaged Lead
Qualified Lead
Discovery Opportunity
Qualified Opportunity
Proposal
Negotiation
Deferred / Paused
Closed Won
Closed Lost
```

This preserves the conversion boundary and makes it clear whether the record is still a lead or has become an opportunity.

## Operating Rules

- Do not treat `Lead.status=qualified` and `Opportunity.stage=qualified` as interchangeable.
- Use `deferred` for viable leads that should be reviewed later.
- Use `paused` for viable opportunities that should be reviewed later.
- Use `disqualified` or `closed-lost` only when the relationship or opportunity is actually no longer viable.
- `waiting` tasks are the reminder mechanism for deferred and paused states.
- Converted leads should preserve provenance to the records created from them.
- Pre-close commercial work should center on the `Opportunity`.
- Post-close execution work should center on the `Engagement`, with concrete delivery lanes represented as `Workstreams`.
