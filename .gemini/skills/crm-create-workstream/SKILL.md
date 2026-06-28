# Skill: CRM Create Workstream

## Description
Creates a canonical `Workstream` under an existing `Engagement`. This is a supporting creation workflow, not a top-level commercial decision loop.

## Usage
`crm-create-workstream --engagement "Engagements/Example" --workstream-type research --name "Market Validation Track"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Confirm that the target `Engagement` already exists.
3. Use `python3 scripts/engagement_manager.py create-workstream ...`.
4. Populate canonical workstream fields from `docs/schema-spec.md`.
5. Link follow-up `Tasks`, `Activities`, `Notes`, and `Source Artifacts` to the workstream as needed.

## Notes

- Do not create orphan workstreams.
- Prefer this as a sub-workflow under `crm-engagement-manager`.
- The current implementation path is `python3 scripts/engagement_manager.py create-workstream ...`.
