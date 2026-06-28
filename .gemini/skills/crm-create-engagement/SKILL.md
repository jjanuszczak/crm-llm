# Skill: CRM Create Engagement

## Description
Creates a canonical `Engagement` for commercially won work using the engagement manager once implemented. This is the preferred creation path for pilots, retainers, advisory mandates, and other post-close work.

## Usage
`crm-create-engagement --account "Accounts/Example" --source-opportunity "Opportunities/Example" --engagement-type advisory`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Confirm that the work is commercially won and no longer belongs only on an `Opportunity`.
3. Use `python3 scripts/engagement_manager.py create ...`.
4. Populate canonical fields from `docs/schema-spec.md`.
5. After creation, use `crm-engagement-manager` to add workstreams and related finance records.

## Notes

- Prefer this over raw hand-authored engagement files.
- Use this as a supporting workflow under `crm-engagement-manager`, `crm-daily-processing`, or explicit commercial close handling.
- The current implementation path is `python3 scripts/engagement_manager.py create ...`.
