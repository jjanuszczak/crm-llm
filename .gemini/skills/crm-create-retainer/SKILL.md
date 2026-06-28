# Skill: CRM Create Retainer

## Description
Creates a canonical `Retainer` under an existing `Engagement`. This is a supporting creation workflow under `crm-finance-manager`.

## Usage
`crm-create-retainer --engagement "Engagements/Example" --amount 5000 --currency USD --cadence monthly`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Resolve the target engagement.
3. Use `scripts/finance_manager.py create-retainer` or the canonical skill-owned implementation.
4. Populate canonical retainer fields from `docs/schema-spec.md`.

## Notes

- Prefer this over storing retainer state only in engagement narrative prose.
- Current implementation exists in:
  - `.gemini/skills/crm-finance-manager/scripts/finance_manager.py`
  - `scripts/finance_manager.py`
