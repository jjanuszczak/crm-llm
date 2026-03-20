# Implementation Plan: Upgrade crm-ingest-gws to Workspace Ingestion Agent

## Phase 1: Architectural Foundation (Normalization)
**Goal**: Decouple source fetching from CRM matching.

- **Task 1.1**: Define and implement the `WorkspaceEvent` canonical schema in `ingest.py`.
- **Task 1.2**: Refactor the script into a modular pipeline:
    - `SourceHarvester`: Fetches Gmail/Calendar deltas.
    - `EventNormalizer`: Maps `gws` JSON to `WorkspaceEvent`.
    - `EntityResolver`: Matches participants to CRM objects.
    - `MutationEngine`: Produces `ProposedAction` objects.
- **Task 1.3**: Update `workspace_updates.json` to support the new `ProposedAction` schema (including confidence and rationale).

## Phase 2: Advanced Entity Resolution & Inference
**Goal**: Increase matching precision and extract intent.

- **Task 2.1**: Implement Multi-Tiered Matching:
    - Tier A: Exact Email.
    - Tier B: Domain match to Account + Name similarity.
    - Tier C: Thread context (e.g., "appears in thread with [Contact]").
- **Task 2.2**: Implement Signal Extraction:
    - Use regex and pattern matching to detect:
        - **Commitments**: "I'll follow up", "Please send", "Meeting next week".
        - **Introductions**: "Meet [Name]", "Intro to".
        - **Commercial Intent**: "Proposal", "Pricing", "Agreement".
- **Task 2.3**: Assign Confidence Scores based on match type and signal strength.

## Phase 3: Three-Tier Write Policy
**Goal**: Automate safe tasks while preserving human oversight for critical changes.

- **Task 3.1**: Implement Policy Logic:
    - **Tier 1 (Safe-Auto)**: Log interaction for existing Contact/Opportunity.
    - **Tier 2 (Auto with Audit)**: Create new Contact if linked to active Opportunity thread.
    - **Tier 3 (Review Required)**: Create new Lead/Account/Opportunity or change stages.
- **Task 3.2**: Update the script CLI to allow setting the max auto-tier (e.g., `--auto-tier 2`).

## Phase 4: Auditability & Telemetry Integration
**Goal**: Improve transparency and feed the Intelligence Engine.

- **Task 4.1**: Implement an `ingestion_audit.json` log to record:
    - Total items scanned.
    - Items ignored (with reason: e.g., "Noise Domain").
    - Actions taken/proposed.
- **Task 4.2**: Feed interaction signals (frequency, sentiment, commitments) directly into `crm-data/staging/interactions.json` to assist the `update-dashboard` intelligence layer.

## Phase 5: Documentation & Validation
**Goal**: Ensure the skill remains agent-friendly and robust.

- **Task 5.1**: Update `SKILL.md` with instructions for managing the new pipeline and review queue.
- **Task 5.2**: Add unit tests for the Normalizer and Resolver components.
- **Task 5.3**: Re-package and re-install the `.skill` file.
