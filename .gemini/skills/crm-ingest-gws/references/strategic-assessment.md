# Strategic Assessment: Workspace Ingestion Agent

## Overview
This document analyzes the current `crm-ingest-gws` implementation against the "Ambient Ingestion and Entity-Resolution" strategy.

### 1. Strategic Alignment Analysis

| Feature | Current Implementation | Expert Strategy Alignment |
| :--- | :--- | :--- |
| **Primary Goal** | Sync and create records. | **Trusted state changes & prioritized suggestions.** |
| **Pipeline** | Fetch → Match → Stage. | **Observe → Normalize → Resolve → Infer → Propose → Log.** |
| **Normalization** | Maps `gws` output directly to CRM templates. | **Unified `WorkspaceEvent` schema** before any CRM logic. |
| **Resolution** | Exact email match only. | **Multi-tiered** (Email, Domain+Name, repeated thread context). |
| **Inference** | Agent-led reasoning during processing. | **Structured "Fact" extraction** (Intros, Commitments, Intent). |
| **Write Policy** | Binary (Autonomous vs. Interactive). | **Three-Tier Policy** (Safe-auto, Reversible-auto, Approval-required). |
| **Memory** | Writes to Markdown Vault (Structured). | **Structured, Episodic (Timeline), and Semantic (Intelligence).** |

---

### 2. Gap Assessment

The existing skill is a functional "v1" that performs the heavy lifting of fetching and basic matching. However, there are significant gaps in **inference depth** and **architectural decoupling**:

1.  **Normalization Layer**: Currently, the ingestion script maps Gmail/Calendar fields directly to CRM proposals. If you add a third source (e.g., LinkedIn or Slack), the logic breaks. The strategy recommends a "Common Event Model" first.
2.  **Explicit Signal Taxonomy**: The current skill treats every non-contact as a "Discovery." The strategy suggests a nuanced taxonomy (Strong/Weak/Negative signals) to prevent noise before it reaches the staging files.
3.  **Confidence & Rationale**: Current proposals don't carry a "Confidence Score" or "Rationale" in the JSON. The agent has to "re-reason" why an item was staged when reviewing it.
4.  **Auditability**: There is no audit log of *ignored* items or *transformation results*, making it hard to debug why a specific contact was missed or why a discovery was filtered.

---

### 3. Recommendations for Upgrade

To align with the "Workspace Ingestion Agent" vision, I recommend the following upgrades:

#### A. Architectural: Components over Monolith
*   Refactor `ingest.py` into a modular pipeline:
    1.  **Harvester**: Pure `gws` acquisition and checkpointing.
    2.  **Normalizer**: Transform `gws` JSON into a `WorkspaceEvent` (standardizing headers, participants, and body).
    3.  **Resolver**: Run matching logic (Email match → Domain match → Name-only fuzzy match).
    4.  **Inferrer**: Scan body text for "Commitments" (tasks) and "Commercial Intent" (opportunities).

#### B. Logic: Implement a Signal Taxonomy
*   Update the `Discovery` logic to categorize candidates:
    *   **High Confidence**: Participants in meetings with known strategic accounts.
    *   **Medium Confidence**: Professional domains with multiple interactions.
    *   **Low Confidence/Noise**: One-off inbounds or non-professional domains (already partially implemented with noise filters).

#### C. Policy: Three-Tier Write Strategy
*   Instead of a single `--autonomous` flag, implement:
    *   **Tier 1 (Auto)**: Update `last-contacted` and append activity logs for existing contacts.
    *   **Tier 2 (Auto with Audit)**: Create new Contacts for participants in existing Opportunity threads.
    *   **Tier 3 (Approval)**: Creating new Organizations or changing Opportunity stages.

#### D. Data: Enrich the Staging Schema
*   Update `workspace_updates.json` and `discovery.json` to include:
    *   `confidence_score`: 0.0 to 1.0.
    *   `rationale`: "Matched via domain @aboitizpower.com to existing Account."
    *   `signals`: `["commitment_detected", "introduction_detected"]`.

#### E. Memory: Semantic Integration
*   The `update-dashboard` script currently handles the "Intelligence" (Semantic) layer. The Ingestion skill should explicitly feed "Relationship Strength" signals into the `interactions.json` telemetry to automate warmth-score updates.
