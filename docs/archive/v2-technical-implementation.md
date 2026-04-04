# Technical Implementation: CRM v2.0 Intelligence Layer

## 1. Schema Updates (Templates)
All entity files must support the new intelligence metrics.

### 1.1 Account & Contact Metadata
Update `templates/account-template.md` and `templates/contact-template.md` YAML:
```yaml
warmth-score: 0-100 # Calculated by the engine
warmth-status: "warm" | "neutral" | "cold"
last-contacted: YYYY-MM-DD
days-since-contact: Number
```

## 2. The Intelligence Engine (`scripts/intelligence-engine.py`)
A new core Python script responsible for the "Affinity" logic.

### 2.1 Warmth Calculation Logic
- **Formula:** `Score = 100 * (1 - (DaysSinceContact / PriorityLimit))`
- **Thresholds:**
    - `high` priority: 14 days
    - `medium` priority: 30 days
    - `low` priority: 90 days
- **Processing:**
    1. Parse all `Activities/` for the most recent `activity-date` per link.
    2. Parse the inbox/calendar cache from `sync-workspace` for more recent interactions.
    3. Update the YAML frontmatter in `crm-data/` files.

### 2.2 Dashboard Generation
- Aggregate all entities with `warmth-status: "cold"` into the **"At-Risk"** section of `INTELLIGENCE.md`.
- Read from `staging/discovery.json` to populate the **"New Discoveries"** section.

## 3. Discovery Workflow (AI Filter)
Enhancing the `sync-workspace` skill.

### 3.1 Domain Filtering
Hardcode a `noise_domains.json` (or include in script) containing:
- Generic: `@gmail.com`, `@outlook.com`, `@hotmail.com`, etc.
- Service: `@zoom.us`, `@doordash.com`, `@uber.com`, `@slack.com`.

### 3.2 Contextual AI Classification
When `sync-workspace` finds a new email address:
1. **Fetch Thread Snippet:** Get the last 3 messages from the thread.
2. **LLM Analysis:** "Determine if this sender is a Professional Prospect (Startup Founder, VC, Corporate) or Noise (Marketing, Logistics, Personal)."
3. **Staging:** If Professional, append to `crm-data/staging/discovery.json` with a "Rationale" field.

## 4. LinkedIn Mapping (Agent-Assisted)
A new workflow within the agent loop.

### 4.1 "Surgical Scrape" Strategy
1. **Trigger:** `create-deal` or manual command `map-deal [url]`.
2. **Browser Execution:** Use Chrome DevTools to navigate to the "People" or "About" tab of the LinkedIn URL.
3. **Extraction:** Capture names, titles, and profile URLs of key leadership.
4. **Graph Matching:** Compare extracted names against `crm-data/Contacts/` to find second-degree connections.

## 5. User Interaction Patterns
New commands to support the "Inbox" workflow:
- `approve-discovery [name]`: Moves a staged discovery from `INTELLIGENCE.md` to a formal file using templates.
- `ignore-discovery [name]`: Moves to a permanent ignore list.
- `refresh-intelligence`: Forced run of the engine and dashboard update.

## 6. Integration Hook
Update `.gemini/skills/update-dashboard/scripts/update-dashboard.py` to:
1. Run standard indexing.
2. Call `intelligence-engine.py`.
3. Output the final `INTELLIGENCE.md` in the `CRM_DATA_PATH`.

---
**Status:** Awaiting Approval to move into Implementation Phase.
