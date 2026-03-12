# PRD: Personal CRM v2.0 – The Intelligence Layer

## 1. Executive Summary
Transform the current "System of Record" (manual logging) into a **"System of Intelligence"** (proactive relationship management) modeled after Affinity CRM. The goal is to minimize data entry while maximizing "Warmth" visibility and "Warm Path" discovery for Venture Brokerage.

## 2. Core Pillars & Features

### Pillar 1: Relationship Depth (Warmth Scoring)
- **Priority-Driven Decay:** Calculate a `warmth-score` for every Account and Contact.
  - **High Priority:** Goes "Cold" after 14 days of no interaction.
  - **Medium Priority:** Goes "Cold" after 30 days.
  - **Low Priority:** Goes "Cold" after 90 days.
- **Interaction Engine:** Aggregate interaction data from `Activities/` and Gmail/Calendar syncs to reset the "last-contacted" date.

### Pillar 2: Passive Discovery (The "Intelligence" Filter)
- **Gmail/Calendar Scanner:** Automatically identify "New Entities" (Contacts/Accounts) from your inbox.
- **Dual-Layer Filtering:**
  - **Domain-Negative:** Ignore common consumer/noise domains (e.g., `@gmail.com`, `@zoom.us`, `@doordash.com`).
  - **Contextual-Positive (AI):** Use LLM analysis of the first email/invite to determine if the entity is a "Startup," "Investor," or "Corporate."
- **Queue System:** Discovered entities are staged in the `INTELLIGENCE.md` dashboard for approval before file creation.

### Pillar 3: Warm Pathing (LinkedIn Intelligence)
- **Agent-Assisted Mapping:** For any new `Deal`, use browser tools to scrape key employees and investors from LinkedIn.
- **Cross-Referencing:** Automatically match LinkedIn "Key People" against the existing `Accounts/` and `Contacts/` folders to identify "Warm Paths" (e.g., "Account [X]'s MD is an investor in Deal [Y]").

### Pillar 4: The Intelligence Interface (`INTELLIGENCE.md`)
- **Central Command:** A single, auto-generated dashboard that serves as your daily CRM "Inbox."
- Section 1: **⚠️ At-Risk Relationships:** High/Medium priority accounts that have "gone cold."
- Section 2: **✨ New Discoveries:** AI-vetted contacts found in Gmail awaiting "Create" approval.
- Section 3: **🔗 Warm Paths:** Suggested connections between active Deals and your existing Network.

## 3. Technical Implementation Strategy
- **`intelligence-engine.py`:** A new Python script to calculate warmth scores and process discovery logs.
- **`sync-workspace` Enhancement:** Update the existing skill to include the "Contextual AI Filter" and output to a `staging.json` file.
- **Template Updates:** Add `warmth-score` and `last-contacted` to YAML frontmatter.
- **Automation Hook:** Run the intelligence engine as part of the `update-dashboard` workflow.

## 4. Success Metrics
- **Zero-Manual-Discovery:** All new professional contacts are identified by the agent first.
- **Retention:** 100% visibility on "High Priority" accounts so none ever stay "Cold" for >48 hours without a task being created.
