# PRD: CRM v4.0 – The Memory System

**Status:** Draft for Review
**Author:** Senior Product Manager
**Target User:** Single principal operator
**Product Form:** AI-first personal CRM built on a private markdown/git vault, with Google Workspace as the primary connected system

## 1. Executive Summary
CRM v4.0 evolves the current system from an intelligence layer into a trustworthy memory system for relationship-led advisory work. The product's primary job is to turn fragmented interactions, notes, email, meetings, tasks, and emerging opportunities into a durable, queryable, AI-usable record of truth.

The system remains local-first and vault-native. Markdown files in a private git-backed vault remain the source of record. AI agents use that vault, plus Google Workspace signals, to maintain a high-quality representation of people, accounts, leads, opportunities, notes, and activities.

This version introduces three major shifts:
- `Lead` becomes a first-class pre-conversion entity with explicit statuses and default conversion into `Contact + Account + Opportunity`.
- `Note` becomes a first-class record type rather than an overloaded inbox substitute.
- The old "Notes as inbox" concept is replaced by a dedicated `Inbox/` capture layer for raw intake and AI triage.

The default daily experience is a relationship dashboard. Tasks, timeline, and recommendations support that dashboard, but do not replace it as the primary surface.

## 2. Product Vision
Build the gold-standard AI-first personal CRM for advisors, consultants, and dealmakers by making relationship context trustworthy, current, and actionable without requiring heavy manual CRM discipline.

## 3. Product Goal
Create a system the user and AI agents can rely on to accurately answer:
- Who matters most right now?
- What is the true state of this relationship?
- What happened recently?
- What should happen next?
- What is still only a prospect versus what has converted into a real engagement?

## 4. Product Principles
- Markdown vault is the system of record.
- AI is a collaborator, not a black box.
- Trust beats completeness.
- Relationships come before pipeline views.
- Structured records and freeform context must coexist.
- Autonomous and interactive modes are both first-class.
- The model should fit advisory work first, without breaking dealmaking or general personal CRM use cases.

## 5. Primary User
A single principal operator who manages a network across clients, prospects, partners, founders, investors, and active engagements.

## 6. Prioritized Jobs To Be Done
1. Reconstruct relationship context quickly and accurately.
2. Maintain a high-trust memory for AI agents operating on the user's behalf.
3. Prevent important relationships from going stale.
4. Surface the right next action.
5. Support advisory, consulting, and dealmaking workflows in one system.

## 7. Core Problems
- Important context is fragmented across email, meetings, tasks, notes, and ad hoc files.
- The current model overloads Notes as both context and intake queue.
- The current entity model starts too late in the funnel; it lacks a true pre-conversion lead state.
- Activities and notes are not yet modeled in a way that supports a gold-standard CRM timeline.
- AI can assist, but the product does not yet fully distinguish between observation, suggestion, and trusted state mutation.

## 8. Product Outcomes

### Primary Outcome
The system becomes a trustworthy memory layer that the user and AI agents can lean on confidently.

### Secondary Outcomes
- Important relationships are less likely to be dropped.
- Recommended next actions are more relevant and timely.
- Conversion from weak prospect signal to live relationship/opportunity is easier and more structured.

## 9. Scope

### In Scope for Day One
- Private markdown/git vault
- Google Workspace integration
- Gmail
- Calendar
- Tasks
- Relationship dashboard as home view
- First-class Leads
- First-class Notes
- Dedicated Inbox
- Unified relationship memory model
- Interactive and autonomous operating modes

### Out of Scope for Day One, But Architecturally Anticipated
- LinkedIn messages
- WhatsApp
- SMS
- call logs
- meeting transcripts
- multi-user collaboration and permissions
- SaaS-native hosted architecture

## 10. Information Model
CRM v4.0 should formalize the following first-class record types:
- `Lead`
- `Contact`
- `Account`
- `Opportunity`
- `Deal`
- `Activity`
- `Task`
- `Note`
- `Inbox Item`

### 10.1 Lead
Purpose: pre-conversion entity representing an unqualified or partially qualified person/company relationship.

Expected status model:
- `new`
- `prospect`
- `engaged`
- `qualified`
- `converted`
- `disqualified`

Lifecycle guidance:
- `new`: sparse early record created from strong inbound signal, inbox triage, manual entry, or AI inference
- `prospect`: plausible relationship candidate with enough identity/context to track
- `engaged`: meaningful two-way communication has occurred
- `qualified`: clear evidence of real commercial or strategic intent exists
- `converted`: lead has been converted into durable records
- `disqualified`: not currently worth pursuing, but may be revived later

Lead records may link to:
- a person
- a company
- source signals
- early notes
- early activities
- proposed next actions

Default conversion behavior:
`Lead -> Contact + Account + Opportunity`

This default reflects the assumption that qualification usually means a concrete advisory or commercial path exists.

Conversion rules:
- A lead may begin as just a person or just a company at early stages.
- A lead must have both person and company populated before conversion is allowed.
- Default conversion creates one primary `Opportunity`.
- Multiple `Opportunity` records may be created from a single lead only when distinct paths are already clear or the user directs it.
- In autonomous mode, conversion may happen automatically only when the specific opportunity is already clear.
- Otherwise, conversion requires approval.
- On conversion, the original lead should be marked `converted` and moved out of the active lead set into an archived location.
- Pre-conversion notes and activities should be copied forward to the converted records.
- Open relationship-building tasks should move primarily to the new `Opportunity`.
- The new `Contact`, `Account`, and `Opportunity` should retain clear provenance back to the source lead.

Revival rules:
- `disqualified` is reversible, not terminal.
- In autonomous mode, strong new evidence may revive a lead automatically.
- Revival should return the lead to `engaged` when the new signal includes meaningful two-way communication.
- Otherwise revival should return the lead to `prospect`.

Lead metadata direction:
- Include a single primary `lead-source` field.
- Include an explicit `owner` field even in the single-operator model.
- `new` leads should be allowed to exist with sparse data such as only an email address, person name, or company name.
- Autonomous creation of `new` leads should require stronger signal than a single inbound message, such as repeated interaction, a meeting, a referral context, or a clearly professional thread.

### 10.2 Contact
Purpose: durable person record after conversion or direct creation.

### 10.3 Account
Purpose: durable organization-level record representing a client, prospect organization, investor, partner, employer, or other relevant entity.

### 10.4 Opportunity
Purpose: a concrete commercial or strategic engagement. Can represent advisory mandates, consulting engagements, brokered matches, or other monetizable work.

### 10.5 Deal
Purpose: inventory seeking capital or strategic matching. Remains distinct from Accounts and Opportunities.

### 10.6 Activity
Purpose: a tracked action or event with temporal meaning. Examples:
- email
- meeting
- call
- task completion
- intro made
- follow-up sent

Activities are measurable and should power timelines, productivity understanding, and relationship recency/velocity.

### 10.7 Task
Purpose: explicit next action owned by the principal operator.

### 10.8 Note
Purpose: durable context, intelligence, interpretation, research, or background information. Notes are not inbox items. Notes should be reportable, linkable, and visible in the relationship record.

Model guidance:
- Notes should stay type-light in v4 and rely primarily on links plus content.
- Notes should generally attach to at least one core record.
- Notes should support one primary parent plus optional secondary links.
- Primary parent precedence should be `Opportunity`, then `Contact`, then `Account`.
- Notes should appear on the unified timeline by default.
- Strategic thinking, research, and background context that are not tied to a discrete event may exist as `Note`-only records with no corresponding `Activity`.

### 10.9 Inbox Item
Purpose: raw captured input awaiting triage, structuring, summarization, or conversion. Inbox replaces the old "Notes as inbox" pattern.

Examples:
- pasted meeting notes
- forwarded thread summary
- raw research snippet
- unstructured idea
- voice transcript summary
- AI-captured signal needing review

Processing guidance:
- Inbox items are temporary by default.
- Inbox items are expected to be processed into durable records and then deleted from the active queue.
- A single Inbox item may generate multiple outputs in one pass, such as a `Note`, `Activity`, and `Task`.
- Create a `Note` from Inbox content only when it has durable contextual value beyond a single action or event.

## 11. Relationship Between Notes, Activities, and Inbox
This version should adopt the v4 distinction explicitly:
- `Inbox` is for raw intake.
- `Notes` are for durable context.
- `Activities` are for things that happened or will happen.
- `Tasks` are for explicit next actions.

The user should experience these as a unified relationship memory, while the underlying records remain distinct.

Additional rules:
- If Inbox content is related to a real event or interaction, it should produce an `Activity`.
- A `Note` may also be created from that same input, but it does not replace the `Activity`.
- `Activity` should follow the same parent-linking pattern as `Note`: one primary parent plus optional secondary links.
- Primary parent precedence for `Activity` should be `Opportunity`, then `Contact`, then `Account`.

## 12. Core User Experience

### 12.1 Home View: Relationship Dashboard
The default morning view should prioritize people and accounts, not just chronology.

It should answer:
- Which relationships need attention?
- Which relationships are active or heating up?
- Which leads are becoming real?
- Which opportunities are at risk?
- What context should I remember before reaching out?

Suggested dashboard sections:
- Priority Relationships
- At-Risk Relationships
- Recently Active Relationships
- Leads Near Conversion
- Open Opportunities by momentum
- Recommended Next Actions
- Inbox Triage Queue
- Recent Notes Worth Reviewing

Priority order for the home dashboard:
1. relationships needing attention
2. recently active / heating up relationships
3. qualified leads / near-conversion
4. recommended next actions

Dashboard ranking guidance:
- The top relationship sections should be driven by a composite attention score rather than elapsed time alone.
- That score should combine signals such as warmth, recency, velocity, relationship priority, and opportunity value.
- If explicit opportunity size is known, it should feed the score directly.
- When explicit size is unknown, AI may incorporate inferred commercial or strategic potential.
- The UI should show separate visible signals, such as `warmth`, `velocity`, and `priority`.
- AI may still use a composite internal score to rank and summarize relationships.
- The main relationship sections should focus on converted entities plus important `qualified` leads.
- `new`, `prospect`, and most `engaged` leads should not dominate the main relationship dashboard.

### 12.2 Unified Relationship Memory
Each key entity should feel like it has one usable memory surface, even if backed by several record types:
- timeline of activities
- linked notes
- current status
- latest AI summary
- open tasks
- lead/opportunity state
- relationship warmth/velocity

### 12.3 Timeline
A unified timeline should merge:
- Activities
- Notes
- key conversions
- task completions
- major AI-derived state changes

## 13. Operating Modes

### Interactive Mode
AI proposes:
- record creation
- conversions
- state changes
- relationship summaries
- task generation

User approves, edits, or rejects.

### Autonomous Mode
AI may perform approved categories of actions automatically, especially:
- ingesting Google Workspace signals
- creating low-risk activities
- updating recency/velocity telemetry
- triaging Inbox items
- drafting summaries
- generating dashboards

High-impact actions should still be auditable and reversible through git history and explicit logs.

## 14. Functional Requirements

### 14.1 First-Class Inbox
- Introduce `Inbox/` as the raw capture surface.
- Inbox items must be triageable into Notes, Activities, Leads, Contacts, Accounts, Opportunities, or Tasks.
- Inbox items should preserve source provenance.
- AI should support both batch triage and per-item interactive processing.

### 14.2 First-Class Notes
- Notes must have their own schema, metadata, and links.
- Notes must be attachable to Leads, Contacts, Accounts, Opportunities, and Deals.
- Notes must appear in the unified relationship memory.
- Notes should support AI summarization into higher-level relationship understanding.

### 14.3 Lead Lifecycle
- Lead creation may originate from inbox, Gmail, Calendar, manual creation, or AI inference.
- Lead status must be explicit and queryable.
- Lead conversion must create `Contact + Account + Opportunity` by default.
- Pre-conversion notes and activities must remain visible after conversion.
- Conversion history must be preserved in the timeline.
- Leads should support both person-led and account-led prospecting early, even if one side is missing.
- Qualified leads must have both a person and a company before they can convert.
- Disqualified leads should be excluded from default dashboard views but remain available through search, filtering, and revival flows.

### 14.4 Relationship Dashboard
- Must prioritize people/accounts over raw activity feed.
- Must surface current relationship health, active context, and suggested next actions.
- Must support lead, contact, account, and opportunity prioritization in one place.
- Must allow important qualified leads to appear alongside converted entities in relationship views.

### 14.5 Trustworthy Memory Layer
- The system must preserve provenance for AI-derived assertions.
- It must separate observed facts from inferred conclusions.
- It must support concise, current "what matters" summaries for key records.
- AI summaries must be regenerable from underlying records.
- AI-generated summaries do not need to inline evidence by default if the user can drill down into the underlying notes, activities, and source records on demand.

### 14.6 Google Workspace Integration
Day one integration should support:
- Gmail as interaction and discovery source
- Calendar as meeting and recency source
- Tasks as task sync source
- optional Contacts as enrichment source

The system should:
- ingest interaction signals
- map them to known entities when possible
- propose or create activities
- identify likely new leads
- update relationship recency and momentum
- support summary generation from thread/event context

### 14.7 Relationship Intelligence
Continue and extend v2/v3 logic:
- warmth
- recency
- velocity
- account-level aggregation
- at-risk detection
- momentum detection
- next-step recommendations

These should now feed the memory system rather than behave as a separate intelligence sidecar.

### 14.8 AI Summaries and Recommendations
For any key relationship, AI should be able to generate:
- current status summary
- recent interaction summary
- unresolved threads
- next best action
- open questions
- recommended note or task creation

## 15. Non-Functional Requirements
- Vault remains human-readable.
- Git history remains auditable.
- Record schemas should be explicit but lightweight.
- AI actions must preserve traceability.
- System should degrade gracefully if external integrations fail.
- Product should remain usable manually without connected services.
- Architecture should anticipate future communication channels without requiring a data model rewrite.

## 16. Data Model Direction
The PRD should drive schema work toward:
- explicit entity types
- stronger links between records
- provenance fields
- status fields for lifecycle-bearing records
- timestamps for observation vs update
- AI summary fields or derived summary artifacts
- stable IDs where useful, even in markdown-native storage

## 17. Success Metrics

### Primary Success Metric
The user can reliably reconstruct relationship context and latest status without manual searching across scattered files and systems.

### Supporting Success Metrics
- AI-generated relationship summaries are judged accurate and useful by the user.
- More interactions are captured automatically from Google Workspace.
- Fewer important relationships go stale without visibility.
- Lead conversion happens with less manual restructuring work.
- Inbox triage burden decreases over time.
- The user can answer "what happened, what matters, what next" for key relationships in one place.

## 18. Key Product Risks
- Over-automation reduces trust if AI writes core records too aggressively.
- Schema expansion makes the vault harder to maintain manually.
- Lead conversion logic could create noisy or premature Opportunities.
- Notes could become another dumping ground if Inbox and Notes are not sharply differentiated.
- Timeline complexity could overwhelm the user if prioritization is weak.
- Google Workspace signals may be incomplete or ambiguous.

## 19. Open Product Questions
- Exact lead status vocabulary and transition rules.
- Exact Note schema and whether notes should support types.
- Exact Inbox item schema and retention/archive behavior.
- How much AI autonomy should be configurable per action category.
- Whether Opportunities need subtypes for advisory, consulting, and brokered work.
- Whether Deals and Opportunities should share more structure or remain intentionally separate.

## 20. Release Framing

### v4 Theme
From "system of intelligence" to "system of memory."

### Release Headline
A relationship-first personal CRM that gives both the user and AI agents a trustworthy memory of who matters, what happened, and what should happen next.
