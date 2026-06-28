# Skill: CRM Finance Manager

## Description
Manages lightweight post-close commercial tracking in the CRM, including `Retainer`, `Invoice`, and `Payment` records. Use this skill when the user wants to track what has been billed, what has been paid, what remains outstanding, and which engagement or workstream those obligations belong to.

This skill owns the workflow question:

- "What commercial obligation exists after close, and what is its current billing or payment state?"

## When To Use
- A retainer should be created for an active engagement.
- An invoice should be issued, updated, or reviewed.
- A payment should be logged or reconciled.
- The user wants to know what is outstanding for an engagement.
- The user wants to understand whether a billing item belongs to the engagement, a workstream, or a retainer period.

## Workflow

1. **Orient to the commercial context**
   - Read `crm-data/index.md` first when locating the engagement cluster.
   - Read the target `Engagement` and, when relevant, the linked `Workstream` or `Retainer`.
   - Read `crm-data/log.md` when recent mutation history may affect interpretation.

2. **Choose the right motion**
   - `create-retainer`
   - `create-invoice`
   - `record-payment`
   - `set-status`
   - `review`

3. **Preserve finance scope**
   - Keep this as lightweight commercial tracking, not full accounting.
   - Tie records to `Engagement` first, and to `Workstream` only where useful.
   - Preserve provenance to external accounting systems when they exist.

4. **Preserve repo policy**
   - Use canonical fields from `docs/schema-spec.md`.
   - Mutation workflows must update `crm-data/index.md` and append `crm-data/log.md`.
   - Prefer explicit finance records rather than burying billing state inside notes.

## User-Facing Usage

The user can ask for:
- "Create a monthly retainer for this engagement."
- "Issue an invoice for the strategy workstream."
- "Record that payment was received."
- "Show me what is overdue for this client."

## Implementation Surface

Canonical implementation:
- `.gemini/skills/crm-finance-manager/scripts/finance_manager.py`

Compatibility wrapper:
- `scripts/finance_manager.py`

Supporting creation skills:
- `crm-create-retainer`
- `crm-create-invoice`
- `crm-create-payment`

## Current Implementation Notes
- The canonical implementation is `.gemini/skills/crm-finance-manager/scripts/finance_manager.py`.
- The compatibility wrapper is `scripts/finance_manager.py`.
- Current implementation support covers:
  - retainer creation
  - invoice creation
  - payment recording
  - status changes for retainers, invoices, and payments
  - review of engagement, invoice, and retainer finance state
  - automatic invoice reconciliation from linked payment records
