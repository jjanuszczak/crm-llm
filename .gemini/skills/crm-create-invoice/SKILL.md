# Skill: CRM Create Invoice

## Description
Creates a canonical `Invoice` under an existing `Engagement`, and optionally links it to a `Workstream` or `Retainer`.

## Usage
`crm-create-invoice --engagement "Engagements/Example" --workstream "Workstreams/Example" --amount 2500 --currency USD`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Resolve the target engagement and optional workstream or retainer.
3. Use `scripts/finance_manager.py create-invoice` or the canonical skill-owned implementation.
4. Populate canonical invoice fields from `docs/schema-spec.md`.

## Notes

- Prefer this over storing invoice state only in notes or activities.
- Current implementation exists in:
  - `.gemini/skills/crm-finance-manager/scripts/finance_manager.py`
  - `scripts/finance_manager.py`
