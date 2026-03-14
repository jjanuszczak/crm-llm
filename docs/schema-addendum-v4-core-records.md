# Schema Addendum: CRM v4.0 Core Records

**Status:** Draft
**Depends On:**
- [prd-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/prd-v4-memory-system.md)
- [implementation-plan-v4-memory-system.md](/Users/johnjanuszczak/Projects/crm-logic/docs/implementation-plan-v4-memory-system.md)

## 1. Purpose
This document defines the minimum viable v4 schema direction for the new or significantly changed core record types:
- `Lead`
- `Inbox Item`
- `Note`
- `Activity`

The goal is to unblock implementation while keeping the markdown/git vault human-readable and preserving room for iteration.

## 2. Design Principles
- Frontmatter should be explicit but lightweight.
- Schemas should support manual editing without making the vault painful to maintain.
- Records should distinguish current business state from provenance and AI-derived metadata.
- Linking should be consistent across record types.
- Each record should support AI summarization and retrieval without requiring excessive denormalization.

## 3. Shared Conventions

### 3.1 Common Fields
These fields should be used where relevant across multiple record types:

```yaml
id: "uuid-or-stable-id"
status: "record-specific-status"
owner: "person-or-agent-identifier"
date-created: YYYY-MM-DD
date-modified: YYYY-MM-DD
source: "primary-source"
source-ref: "optional external or internal reference"
```

Guidance:
- `id` should be stable and machine-friendly.
- `owner` should exist even in the single-operator model.
- `source` is the primary origin signal, not a complete provenance log.
- `source-ref` may store a message ID, event ID, inbox item ID, or other pointer.

### 3.2 Linking Model
`Note` and `Activity` should use:
- one `primary-parent`
- optional `secondary-links`

Primary parent precedence:
1. `Opportunity`
2. `Contact`
3. `Account`

Recommended frontmatter pattern:

```yaml
primary-parent-type: "opportunity"
primary-parent: "[[Opportunities/Example-Opportunity]]"
secondary-links:
  - "[[Contacts/Jane-Doe]]"
  - "[[Accounts/Example-Capital]]"
```

### 3.3 Observed vs Inferred
Where a record includes AI interpretation, prefer fields that preserve the distinction between:
- observed facts
- inferred state

This does not require a heavy evidence model in every file, but the schema should leave room for it.

## 4. Lead

### 4.1 Purpose
Represents a pre-conversion relationship candidate that may begin sparse and become richer over time.

### 4.2 Minimum Viable Fields

```yaml
id: "lead-uuid"
lead-name: "Jane Doe or Example Capital"
status: "new"
owner: "john"
lead-source: "gmail"
person-name: "Jane Doe"
company-name: "Example Capital"
email: "jane@example.com"
linkedin: "https://..."
source-ref: "gmail-message-id-or-other-ref"
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 4.3 Field Guidance
- `lead-name`: display label for the lead record
- `status`: one of:
  - `new`
  - `prospect`
  - `engaged`
  - `qualified`
  - `converted`
  - `disqualified`
- `lead-source`: single primary source such as:
  - `manual`
  - `gmail`
  - `calendar`
  - `inbox`
  - `referral`
  - `linkedin`
- `person-name` and `company-name` may be partially populated in early stages
- `email` and `linkedin` are optional enrichment fields
- `source-ref` points to the originating message, event, inbox item, or similar source

### 4.4 Optional Fields

```yaml
priority: "high"
phone: "+63..."
notes-summary: "short AI or user-maintained summary"
qualification-signal: "Requested proposal for advisory support"
disqualification-reason: "No relevant mandate"
converted-contact: "[[Contacts/Jane-Doe]]"
converted-account: "[[Accounts/Example-Capital]]"
converted-opportunities:
  - "[[Opportunities/Example-Capital-Advisory]]"
```

### 4.5 Validation Rules
- `new` leads may exist with only one of:
  - `person-name`
  - `company-name`
  - `email`
- `qualified` leads should require both `person-name` and `company-name`
- conversion should not proceed unless both person and company are known
- `converted-*` fields should be populated once conversion happens

### 4.6 File Placement
Recommended active path:
- `Leads/`

Recommended archived path after conversion:
- `Leads/Converted/`

Recommended archived path after disqualification is still unnecessary by default. `disqualified` leads can remain in `Leads/` and be filtered out of active views unless archival becomes operationally necessary.

## 5. Inbox Item

### 5.1 Purpose
Represents temporary raw capture awaiting triage into durable records.

### 5.2 Minimum Viable Fields

```yaml
id: "inbox-uuid"
title: "Raw meeting notes with Jane Doe"
status: "new"
owner: "john"
source: "manual"
source-ref: "optional-ref"
captured-at: 2026-03-14
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 5.3 Status Options
- `new`
- `processing`
- `processed`
- `ignored`

### 5.4 Optional Fields

```yaml
suggested-outputs:
  - "note"
  - "activity"
  - "task"
related-lead: "[[Leads/Jane-Doe-Example-Capital]]"
primary-parent-type: "lead"
primary-parent: "[[Leads/Jane-Doe-Example-Capital]]"
processing-mode: "interactive"
```

### 5.5 Validation Rules
- Inbox items are temporary by default
- processed items should be deletable after durable outputs are created
- one Inbox item may generate multiple outputs
- if the source is clearly event-based, processing should generate an `Activity`

### 5.6 File Placement
Recommended path:
- `Inbox/`

## 6. Note

### 6.1 Purpose
Represents durable context, intelligence, interpretation, research, or strategic memory.

### 6.2 Minimum Viable Fields

```yaml
id: "note-uuid"
title: "Context for Jane Doe relationship"
owner: "john"
primary-parent-type: "contact"
primary-parent: "[[Contacts/Jane-Doe]]"
secondary-links:
  - "[[Accounts/Example-Capital]]"
source: "manual"
source-ref: "optional-ref"
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 6.3 Field Guidance
- `title`: short human-readable label
- `primary-parent-type`: expected values:
  - `lead`
  - `contact`
  - `account`
  - `opportunity`
  - `deal`
  - `activity`
- `primary-parent`: required in normal operation
- `secondary-links`: optional additional links
- `source`: origin such as:
  - `manual`
  - `inbox`
  - `gmail`
  - `calendar`
  - `ai-generated`

### 6.4 Optional Fields

```yaml
summary: "Short note summary"
visibility: "default"
timeline-display: true
```

### 6.5 Validation Rules
- Notes should generally link to at least one core record
- notes remain type-light in v4
- notes may exist without an `Activity` when they are not tied to a discrete event
- notes should appear on the unified timeline by default

### 6.6 File Placement
Recommended path:
- `Notes/`

## 7. Activity

### 7.1 Purpose
Represents a real event, interaction, or completed action with temporal meaning.

### 7.2 Minimum Viable Fields

```yaml
id: "activity-uuid"
activity-name: "Email exchange with Jane Doe"
activity-type: "email"
status: "completed"
owner: "john"
date: 2026-03-14
primary-parent-type: "opportunity"
primary-parent: "[[Opportunities/Example-Capital-Advisory]]"
secondary-links:
  - "[[Contacts/Jane-Doe]]"
  - "[[Accounts/Example-Capital]]"
source: "gmail"
source-ref: "gmail-thread-or-message-id"
date-created: 2026-03-14
date-modified: 2026-03-14
```

### 7.3 Field Guidance
- `activity-type`: expected early values:
  - `email`
  - `meeting`
  - `call`
  - `task-completion`
  - `intro`
  - `follow-up`
  - `note-derived`
- `status`: minimum useful values:
  - `completed`
  - `scheduled`
  - `cancelled`
- `date`: primary event date
- `primary-parent-type` and `primary-parent`: required in normal operation
- `secondary-links`: optional additional links

### 7.4 Optional Fields

```yaml
start-time: "2026-03-14T09:00:00+08:00"
end-time: "2026-03-14T10:00:00+08:00"
summary: "Discussed advisory scope and next steps"
next-step: "Send proposal by Friday"
related-task: "[[Tasks/Send-Proposal-To-Jane-Doe]]"
```

### 7.5 Validation Rules
- if the source record represents a real event or interaction, it should create an `Activity`
- activities should use one primary parent plus optional secondary links
- primary parent precedence should follow:
  1. `Opportunity`
  2. `Contact`
  3. `Account`

### 7.6 File Placement
Recommended path:
- `Activities/`

## 8. Open Schema Questions
- Whether `id` should be UUID-based, slug-based, or dual-format
- Whether `summary` fields should be user-editable, AI-generated, or both
- Whether `source-ref` should be scalar or support multiple refs
- Whether `Activity.status` needs more nuance at v4 launch
- Whether `Note.visibility` is necessary in a single-user product

## 9. Recommended Immediate Follow-On
Use this addendum to:
1. update templates
2. create or revise skill instructions
3. centralize schema parsing/validation helpers
4. design migration rules for legacy `Notes/`
