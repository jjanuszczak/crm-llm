# Skill: CRM Create Payment

## Description
Creates a canonical `Payment` linked to an existing `Invoice`. This is a supporting creation workflow under `crm-finance-manager`.

## Usage
`crm-create-payment --invoice "Invoices/Example" --amount 2500 --currency USD --received-date 2026-06-28`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Resolve the target invoice.
3. Use `scripts/finance_manager.py record-payment` or the canonical skill-owned implementation.
4. Populate canonical payment fields from `docs/schema-spec.md`.

## Notes

- Prefer this over burying payment confirmation only in email activities.
- Current implementation exists in:
  - `.gemini/skills/crm-finance-manager/scripts/finance_manager.py`
  - `scripts/finance_manager.py`
