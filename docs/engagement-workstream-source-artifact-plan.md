# Requirements and Implementation Plan: Engagements, Workstreams, Finance, and Source Artifacts

**Status:** Draft
**Issue:** [#33](https://github.com/jjanuszczak/crm-llm/issues/33)
**Branch:** `codex/engagement-workstream-planning`
**Goal:** Define the requirements, canonical schema direction, and staged implementation plan for expanding the CRM LLM system from pre-close CRM into post-close execution, delivery memory, finance tracking, and cross-system source-artifact handling without implementing code yet.

## 1. Objective

Extend the current relationship-first CRM so it can support:

- commercially won work after `Opportunity`
- multiple parallel execution lanes inside a single client relationship
- invoice, retainer, payment, and exposure tracking
- typed durable knowledge capture without introducing a separate `Insight` entity initially
- a unified source-artifact model for Google Drive, Readwise, Granola, URLs, local files, and future external systems

This enhancement must preserve the markdown/git vault as the system of record and respect the repo contract that mutation workflows update `crm-data/index.md` and `crm-data/log.md`.

## 2. Product Boundaries

### In scope

- post-close commercial and execution modeling
- delivery-related activities, notes, tasks, and linked documents
- lightweight finance tracking at the engagement level
- typed reusable knowledge and research notes
- cross-entity external source references
- future retrieval and workflow extensions built on the new graph

### Out of scope

- replacing Google Drive, Readwise, or other external systems
- full project management suite behavior
- full accounting / ERP behavior
- a separate first-class `Insight` entity in the first phase
- implementation work before the planning and schema direction are agreed

## 3. Core Design Decisions

### 3.1 Commercial boundary

- `Opportunity` remains the pre-close pursuit record.
- A real commercial commitment, including a pilot, becomes an `Engagement`.
- Significant unpaid or ambiguous pre-close work remains represented through `Activities`, `Notes`, `Tasks`, and relationship heat inside the opportunity layer.

### 3.2 Execution boundary

- `Engagement` is the post-close commercial and execution container.
- `Workstream` is the generalized execution lane within an engagement.
- Every `Workstream` must belong to exactly one `Engagement`.
- No orphan `Workstream` records should exist.

### 3.3 Knowledge boundary

- `Notes` remain the durable knowledge object.
- `Notes` should be extended with stronger typing, reuse controls, and evidence linking.
- A separate `Insight` entity should be deferred unless future workflows prove `Notes` are overloaded.

### 3.4 External artifact boundary

- External systems remain artifact stores.
- The CRM vault remains the canonical control plane.
- A first-class cross-entity `Source Artifact` record should represent external evidence and documents.
- `Note` records remain the durable interpreted or synthesized memory derived from those source artifacts.

### 3.5 Finance boundary

- Finance tracking becomes in scope once delivery is in scope.
- This layer should answer what was sold, what has been invoiced, what has been paid, and what remains outstanding.
- It should stay CRM-adjacent and lightweight rather than attempting full accounting behavior.

## 4. Target Conceptual Model

1. `Organization`
2. `Account`
3. `Opportunity`
4. `Engagement`
5. `Workstream`
6. `Deliverable` (explicitly deferred until after core engagement/workstream support is stable)
7. `Invoice`
8. `Payment`
9. `Retainer`
10. `Note`
11. `Source Artifact`

## 5. Canonical Entity Responsibilities

### `Opportunity`

Answers: should this work be won?

Responsibilities:
- pre-close commercial pursuit
- relationship development
- proposal / negotiation context
- heavy pre-close activity and research without implying delivery

### `Engagement`

Answers: what commercially won work exists with this client?

Responsibilities:
- post-close commercial container
- source opportunity linkage when applicable
- delivery umbrella for one or more workstreams
- finance summary anchor
- client-facing terms, start/end timing, and execution state

### `Workstream`

Answers: what execution lane exists within this engagement?

Responsibilities:
- advisory lane, research lane, marketing lane, board-support lane, implementation lane, or similar
- operational context for tasks, notes, activities, and source artifacts
- optional home for deliverables

### `Note`

Answers: what durable context, interpretation, or learning should be retained?

Responsibilities:
- synthesized memory
- research and delivery lessons
- decisions and retrospectives
- brand-seed and reusable anonymized learning

### `Source Artifact`

Answers: what external artifact is the evidence or primary document?

Responsibilities:
- canonical pointer to a Drive file, Readwise item, Granola note, URL, local file, or similar
- provenance and confidentiality anchor
- shared reference layer across entities

### `Invoice` / `Payment` / `Retainer`

Answers: what commercial obligation has been agreed, billed, paid, or remains exposed?

Responsibilities:
- invoice status tracking
- retainer period tracking
- payment receipt linkage
- milestone or workstream association when useful

## 6. Required Schema Direction

### 6.1 New entities

The schema should add:

- `Engagements/`
- `Workstreams/`
- `Source-Artifacts/`
- finance records, likely under one of:
  - `Invoices/`, `Payments/`, `Retainers/`
  - or a grouped finance path if that proves cleaner

### 6.2 Parent-link extensions

Current parent-linking should be extended so these entities can participate naturally in memory assembly:

- `Activities.primary-parent-type` should support `engagement` and `workstream`
- `Notes.primary-parent-type` should support `engagement` and `workstream`
- `Tasks.primary-parent-type` should support `engagement` and `workstream`

Secondary linking should also tolerate these new records.

### 6.3 Notes extensions

`Notes` should gain new canonical or compatibility-aware fields for:

- `note-type`
  - examples: `delivery-insight`, `research`, `sales-intelligence`, `decision`, `retrospective`, `brand-seed`
- `reuse-classification`
  - `internal-only`, `client-confidential`, `reusable-anonymized`, `public-safe`
- `evidence-links`
  - source-artifact links, activity links, or other supporting records
- `derived-from`
  - optional lineage to another note or source artifact

### 6.4 Source artifact model

`Source Artifact` should be a generalized external reference object rather than a Google-Drive-only or Readwise-only record.

Candidate fields:

- `id`
- `title`
- `owner`
- `source-system`
  - `google-drive`, `readwise`, `granola`, `gmail`, `url`, `local-file`, `other`
- `source-type`
  - `doc`, `sheet`, `slides`, `pdf`, `folder`, `article`, `book`, `podcast`, `meeting-note`, `email-thread`, `video`, `other`
- `url`
- `external-id`
- `source`
- `source-ref`
- `confidentiality`
  - `internal-only`, `client-confidential`, `reusable-anonymized`, `public-safe`
- `status`
  - `active`, `archived`, `superseded`
- `summary-note`
  - optional note link
- `last-reviewed`
- `date-created`
- `date-modified`

### 6.5 Finance model

The finance layer should begin narrow.

At minimum, it should support:

- `Retainer`
  - engagement link, term, amount, currency, cadence, status
- `Invoice`
  - engagement link, optional workstream / deliverable link, amount, currency, issue date, due date, status
- `Payment`
  - invoice link, amount, currency, received date, method, notes

The design should allow lightweight reporting for outstanding exposure without becoming a full accounting ledger.

## 7. Linking and Relationship Rules

### Required links

- `Workstream` must link to exactly one `Engagement`
- `Invoice` must link to exactly one `Engagement`
- `Payment` must link to at least one `Invoice`

### Optional links

- `Engagement` may link to one source `Opportunity`
- `Invoice` may link to a `Workstream`
- `Invoice` may later link to a `Deliverable`
- `Source Artifact` may link to one or many business records through backlinks or explicit references
- `Note` may link to `Opportunity`, `Engagement`, `Workstream`, `Account`, `Organization`, `Activity`, or `Source Artifact`

## 8. Readwise, Google Drive, and External-System Handling

### Readwise

Readwise should remain the raw capture and annotation system.

The CRM should store:

- a `Source Artifact` pointer to the Readwise item
- a typed `Note` when the material becomes durable business memory
- provenance fields that preserve the upstream item identity

The CRM should not attempt to mirror the full Readwise corpus by default.

### Google Drive

Google Drive should remain the artifact store for large working documents, decks, spreadsheets, folders, and client deliverables.

The CRM should store:

- `Source Artifact` records for important Drive files and folders
- links from `Engagement`, `Workstream`, `Note`, and later `Deliverable` records to those artifacts
- optional summary notes derived from those artifacts

The CRM should not try to absorb every Drive file into markdown.

### General external-source principle

The vault should store:

- the canonical link
- the provenance
- the business meaning
- the entity relationships
- any durable synthesis

The vault should not try to replace the underlying external artifact store.

## 9. Navigation and Mutation Contract Impact

Any new writer workflows introduced for:

- engagement creation
- workstream creation
- finance record creation or updates
- source-artifact creation or updates

must account for:

- `crm-data/index.md` rebuild or refresh
- `crm-data/log.md` append behavior

This is part of the current repo contract and should be treated as a requirement, not polish.

## 10. Dashboard and Retrieval Implications

The current dashboard is relationship-first. That should remain true.

This enhancement should later support a second execution and finance view, likely including:

- active engagements by client
- workstreams by status and owner
- upcoming or overdue delivery tasks
- unpaid invoices and exposure
- recent delivery notes and retrospectives
- reusable anonymized insights by sector or client type

These should be staged after the core schema is stable.

## 11. Phased Implementation Plan

### Phase 0: Design freeze

Objective:
- lock entity responsibilities, parent-linking rules, and source-artifact design

Deliverables:
- agreed schema direction for `Engagement`, `Workstream`, `Source Artifact`, and finance records
- agreed `Notes` extensions
- agreed migration and rollout constraints

Exit criteria:
- no unresolved ambiguity about pre-close versus post-close records
- no unresolved ambiguity about whether `Notes` or `Insight` is the primary knowledge object

### Phase 1: Schema and template foundation

Objective:
- add the new entities and templates without implementing end-to-end workflows yet

Deliverables:
- directory and template decisions
- schema doc updates
- field definitions and statuses
- canonical naming and parent-link rules

Exit criteria:
- valid records for new entities can be created manually
- schema docs reflect the new model

### Phase 2: Parent-link and navigation support

Objective:
- make existing memory primitives aware of engagements and workstreams

Deliverables:
- updated parent-type support in `Activities`, `Notes`, and `Tasks`
- navigation/index support for new record types
- log semantics for new mutation workflows

Exit criteria:
- new entities participate correctly in memory assembly and navigation

### Phase 3: Engagement and workstream workflows

Objective:
- introduce creation and update workflows for post-close execution records

Deliverables:
- engagement creation and review workflow
- workstream creation and status workflow
- opportunity-to-engagement conversion logic

Exit criteria:
- a closed-won or pilot opportunity can cleanly create or link to an engagement
- multiple workstreams can exist under one engagement

### Phase 4: Source-artifact workflows

Objective:
- create a unified external-source reference layer

Deliverables:
- source-artifact creation / linking workflow
- conventions for Readwise and Google Drive linkage
- note-to-source and entity-to-source linking patterns

Exit criteria:
- important external artifacts can be linked once and reused across records
- notes can cite source artifacts cleanly

### Phase 5: Finance workflows

Objective:
- add lightweight commercial tracking after close

Deliverables:
- retainer, invoice, and payment record workflows
- engagement-level outstanding exposure view
- minimal status transitions

Exit criteria:
- post-close commercial visibility exists without needing external accounting systems for every answer

### Phase 6: Retrieval, dashboard, and automation extensions

Objective:
- capitalize on the new graph without destabilizing core record integrity

Deliverables:
- execution dashboard concepts
- finance summary views
- anonymized insight retrieval
- optional future automations for source ingestion, note synthesis, and workstream follow-up

Exit criteria:
- retrieval quality and operator leverage improve materially from the new model

## 12. Migration and Backward-Compatibility Notes

- Existing opportunities must remain readable without engagements.
- Existing notes must remain valid without note typing until migrated or touched.
- Existing source link fields, if present in records, may need temporary compatibility support during transition.
- Existing dashboard and intelligence flows should fail open while the new layer is being introduced.

## 13. Risks

### Semantic overlap

Risk:
- `Opportunity`, `Engagement`, and `Workstream` could blur together.

Mitigation:
- keep hard responsibility boundaries in schema docs and workflow prompts

### Knowledge sprawl

Risk:
- delivery and research notes become a dumping ground

Mitigation:
- typed notes, reuse classification, and stronger linking to source artifacts

### External-link entropy

Risk:
- Drive and Readwise links get duplicated ad hoc

Mitigation:
- first-class `Source Artifact` records

### Finance creep

Risk:
- the system expands into lightweight accounting, then accidental ERP behavior

Mitigation:
- restrict finance scope to engagement-level obligations, billing, and payment state

## 14. Open Questions For Design Review

- `Deliverable` is deferred from the first implementation wave. Revisit it only after engagement and workstream behavior is stable in actual operator use.
- Should finance records live in separate top-level directories or a grouped finance namespace?
- Should `Source Artifact` explicitly store linked entities in frontmatter, or rely primarily on backlinks plus a small set of direct references?
- What minimal workflow should exist for source-artifact review and summarization?

## 15. Immediate Next Step

Before implementation starts:

- convert this plan into explicit schema updates in `docs/schema-spec.md`
- define templates for the new entities
- decide the minimal workflow surface for the first implementation pass
