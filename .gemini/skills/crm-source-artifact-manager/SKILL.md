# Skill: CRM Source Artifact Manager

## Description
Manages cross-entity source references for external artifacts such as Google Drive docs, Readwise items, Granola notes, URLs, PDFs, and local files. Use this skill when the user wants to create, link, review, summarize, or re-parent a `Source Artifact`.

This skill owns the workflow question:

- "What external artifact is the evidence, and where should it be attached in the CRM?"

## When To Use
- A Google Drive file or folder should be linked to an opportunity, engagement, or workstream.
- A Readwise item should become durable business memory with provenance.
- The user wants to avoid duplicating the same external link across multiple records.
- A note should cite or summarize an external source.
- An external artifact needs review, confidentiality classification, or re-linking.

## Workflow

1. **Orient to the business context**
   - Read `crm-data/index.md` first when locating the relationship or execution cluster.
   - Read the target `Opportunity`, `Engagement`, `Workstream`, `Note`, or other parent record.
   - Read `crm-data/log.md` when recent mutation history matters.

2. **Choose the right motion**
   - `create`
   - `link`
   - `review`
   - `re-parent`
   - `set-status`
   - `attach-summary-note`

3. **Preserve evidence boundaries**
   - Keep the external system as the artifact store.
   - Keep the CRM as the canonical control plane.
   - Use one `Source Artifact` for one external artifact whenever possible.
   - Use `Note` for durable interpretation, not `Source Artifact`.

4. **Preserve repo policy**
   - Use canonical fields from `docs/schema-spec.md`.
   - Mutation workflows must update `crm-data/index.md` and append `crm-data/log.md`.
   - Prefer workflow-level judgment over scattered manual link fields.

## User-Facing Usage

The user can ask for:
- "Link this Google Drive folder to the engagement."
- "Create a source artifact for this Readwise article."
- "Attach a summary note to this source document."
- "Review whether this source belongs on the workstream or just the engagement."

## Implementation Surface

Canonical implementation:
- `.gemini/skills/crm-source-artifact-manager/scripts/source_artifact_manager.py`

Compatibility wrapper:
- `scripts/source_artifact_manager.py`

Supporting creation skill:
- `crm-create-source-artifact`

## Current Implementation Notes
- The canonical implementation is `.gemini/skills/crm-source-artifact-manager/scripts/source_artifact_manager.py`.
- The compatibility wrapper is `scripts/source_artifact_manager.py`.
- Current implementation support covers:
  - source artifact creation
  - secondary-link updates
  - primary-parent reassignment
  - summary-note attachment
  - status changes
  - read-only source artifact review
