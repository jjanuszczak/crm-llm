# Skill: CRM Create Source Artifact

## Description
Creates a canonical `Source Artifact` for an external document, evidence item, or linked artifact. This is the preferred creation path for Drive files, Readwise items, Granola notes, external URLs, and similar sources.

## Usage
`crm-create-source-artifact --primary-parent "Engagements/Example" --source-system google-drive --source-type doc --url "https://..."`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Resolve the primary parent record.
3. Confirm the artifact should be represented as a reusable source reference rather than copied into a note body.
4. Use `scripts/source_artifact_manager.py create` or the canonical skill-owned implementation.
5. Create a linked `Note` only when durable interpretation is needed.

## Notes

- Prefer this over scattered ad hoc `google-drive-url` or similar link fields.
- Use this as a sub-workflow under `crm-source-artifact-manager`, `crm-ingest-gws`, or relationship / execution review.
- Current implementation exists in:
  - `.gemini/skills/crm-source-artifact-manager/scripts/source_artifact_manager.py`
  - `scripts/source_artifact_manager.py`
