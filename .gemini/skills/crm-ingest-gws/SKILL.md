---
name: crm-ingest-gws
description: Ambient Workspace Ingestion Agent. Continuously converts communication exhaust from Gmail and Calendar into trusted CRM state changes, candidate entities, and prioritized suggestions using a modular pipeline and multi-tiered matching.
---

# Crm Ingest Gws (Ambient Agent)

## Overview
This skill implements an **Ambient Ingestion and Entity-Resolution Agent**. It doesn't just sync data; it understands interaction context, extracts intent, and proposes or executes CRM updates based on a confidence-driven three-tier policy.

## Workflow

### 1. Ingestion & Analysis Pipeline
Run the ingestion agent to scan deltas and generate prioritized proposals.

```bash
python3 .gemini/skills/crm-ingest-gws/scripts/ingest.py [--since YYYY-MM-DD] [--auto-tier N]
```

- **Harvester**: Incremental sync using `gws` CLI.
- **Normalizer**: Standardizes events into a `WorkspaceEvent` schema.
- **Resolver**: Multi-tiered matching (Email -> Domain -> Account).
- **Inferrer**: Extracts signals: `commitment_detected`, `commercial_intent`, `introduction_detected`, `logistics_detected`.

### 2. Three-Tier Write Policy
The agent categorizes actions into tiers to balance automation with trust:

| Tier | Policy | Action Type |
| :--- | :--- | :--- |
| **1** | Safe-Auto | Update `last-contacted`, append activity to existing Contact/Opportunity. |
| **2** | Auto-with-Audit | Create new Contact for participants in existing Opportunity threads. |
| **3** | Approval Required | Create new Accounts, Leads, Opportunities, or change deal stages. |

- Use `--auto-tier 1` to automate logging for known contacts.
- Use `--auto-tier 2` to automate contact discovery in active deal threads.

### 3. Review Queue
- **Proposals**: `crm-data/staging/workspace_updates.json` (Includes `confidence`, `rationale`, and `signals`).
- **Discoveries**: `crm-data/staging/discovery.json` (Unknown professional contacts).
- **Audit**: `crm-data/staging/ingestion_audit.json`.

## Record Creation Rules
- **Deduplication**: Uses `source-ref` (Gmail ID / Calendar ID) to prevent duplicates.
- **Content Enrichment**: Summarizes body content; never uses subjects alone.
- **Telemetry**: Automatically updates `interactions.json` to feed the Intelligence Engine.

## Tool Integration
Requires `gws` CLI and coordinates with `gws-shared` for authentication.
