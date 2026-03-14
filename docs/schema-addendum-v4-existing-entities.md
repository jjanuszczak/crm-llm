# Schema Addendum: CRM v4.0 Existing Entity Alignment

**Status:** Draft
**Depends On:**
- [prd-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/prd-v4-memory-system.md)
- [schema-addendum-v4-core-records.md](/Users/johnjanuszczak/Projects/crm-logic/docs/schema-addendum-v4-core-records.md)

## 1. Purpose
This document defines recommended v4 updates for the existing entity types that were not fully redesigned in the first pass:
- `Contact`
- `Account`
- `Opportunity`
- `Task`

The goal is to align these records with the v4 memory model so they work consistently with first-class `Lead`, `Inbox`, `Note`, and `Activity` records.

## 2. Cross-Entity Alignment Themes
These changes should be considered across all four entity types where relevant:

- add `id`
- add `owner`
- add `source`
- add `source-ref`
- clarify whether the record's `status` or `stage` reflects relationship state, workflow state, or pipeline state
- reduce reliance on body prose for fields the dashboard and AI memory layer need to reason about
- support provenance from lead conversion, inbox processing, and workspace sync

## 3. Contact

### 3.1 Current Gap
The current Contact model still reflects pre-v4 assumptions:
- no `id`
- no `owner`
- no provenance fields
- ambiguous `status`
- mixed live usage of `full-name` and legacy `full--name`

### 3.2 Recommended v4 Direction

```yaml
id: "contact-jane-doe"
full-name: "Jane Doe"
nickname: "Jane"
owner: "john"
account: "[[Accounts/Example-Capital]]"
deal: "[[Deals/Example-Deal]]"
email: "jane@example.com"
mobile: "+63..."
linkedin: "https://..."
source: "lead-conversion"
source-ref: "[[Leads/Jane-Doe-Example-Capital]]"
relationship-status: "active"
priority: "high"
warmth-score: 0
warmth-status: "neutral"
velocity-score: 0
last-contacted: 2026-03-14
days-since-contact: 0
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 3.3 Recommendations
- make `full-name` canonical and treat `full--name` as legacy
- replace or deprecate `status` in favor of `relationship-status`
- add `priority` directly on Contact so attention ranking does not depend only on Account
- add provenance when a Contact originates from lead conversion

## 4. Account

### 4.1 Current Gap
The current Account template mixes due diligence reporting with CRM state, but lacks v4 provenance and memory support.

### 4.2 Recommended v4 Direction

```yaml
id: "account-example-capital"
company-name: "Example Capital"
owner: "john"
type: "investor"
relationship-stage: "engaged"
priority: "high"
headquarters: "Singapore"
industry: "investment"
url: "https://example.com"
size: 250
source: "lead-conversion"
source-ref: "[[Leads/Jane-Doe-Example-Capital]]"
warmth-score: 0
warmth-status: "neutral"
velocity-score: 0
account-warmth-index: 0
last-contacted: 2026-03-14
days-since-contact: 0
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 4.3 Recommendations
- add `id`, `owner`, `source`, and `source-ref`
- rename or clarify `stage` as `relationship-stage`
- keep DD-heavy body sections, but add enough frontmatter for dashboarding and AI retrieval
- make `size` explicit and consistent if it is used as a commercial signal

## 5. Opportunity

### 5.1 Current Gap
Opportunities remain the operational center of gravity, but the template is still too body-heavy for v4 automation.

### 5.2 Recommended v4 Direction

```yaml
id: "opportunity-example-capital-advisory-2026"
opportunity-name: "Example Capital - Advisory - 2026"
owner: "john"
account: "[[Accounts/Example-Capital]]"
deal: "[[Deals/Example-Deal]]"
primary-contact: "[[Contacts/Jane-Doe]]"
source-lead: "[[Leads/Jane-Doe-Example-Capital]]"
opportunity-type: "advisory"
is-active: true
stage: "proposal"
commercial-value: 250000
close-date: 2026-04-30
probability: 60
product-service: "Strategic Advisory"
source: "lead-conversion"
source-ref: "[[Leads/Jane-Doe-Example-Capital]]"
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 5.3 Recommendations
- add `id`, `owner`, `source`, and `source-ref`
- add `source-lead`
- add `opportunity-type`
- prefer `commercial-value` over `deal-value`, or explicitly document the difference
- move key stakeholder links such as `influencers` into structured frontmatter where possible

## 6. Task

### 6.1 Current Gap
Tasks are the least aligned entity with v4:
- no `id`
- no `owner`
- no provenance fields
- no canonical parent-linking model
- no first-class support for `Lead`

### 6.2 Recommended v4 Direction

```yaml
id: "task-send-proposal-to-jane"
task-name: "Send proposal to Jane"
status: "todo"
priority: "high"
owner: "john"
due-date: 2026-03-20
primary-parent-type: "opportunity"
primary-parent: "[[Opportunities/Example-Capital-Advisory-2026]]"
account: "[[Accounts/Example-Capital]]"
contact: "[[Contacts/Jane-Doe]]"
opportunity: "[[Opportunities/Example-Capital-Advisory-2026]]"
lead: "[[Leads/Jane-Doe-Example-Capital]]"
type: "follow-up"
source: "activity"
source-ref: "[[Activities/Jane-intro-call]]"
email-link: ""
meeting-notes: ""
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 6.3 Recommendations
- add `id`, `owner`, `source`, and `source-ref`
- add `primary-parent-type` and `primary-parent`
- add explicit `lead` support
- expand `status` to a fuller lifecycle such as:
  - `todo`
  - `in-progress`
  - `blocked`
  - `done`
  - `canceled`

## 7. Recommended Backlog Breakdown
Recommended implementation order:
1. Contact alignment
2. Account alignment
3. Opportunity alignment
4. Task alignment

## 8. Immediate Implementation Goal
The first implementation pass should focus on:
- template updates
- skill instruction updates
- backward-compatible parser tolerance where legacy fields already exist

That should happen before deeper automation changes depend on the new fields.
