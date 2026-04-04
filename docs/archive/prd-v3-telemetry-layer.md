# PRD: CRM v3.0 – The Telemetry & Graph Layer

**Status:** Approved | **Author:** Senior Product Manager (Gemini) | **Target:** Zero-Entry Venture Brokerage

## 1. Executive Summary
V3.0 shifts the CRM from a manual "ledger" to an autonomous "observer." By capturing passive telemetry from your inbox/calendar and aggregating individual contact health into account-level intelligence, we provide a real-time map of your "Warmest Paths" to capital and deals.

## 2. Core Objectives
1.  **Zero-Entry Tracking:** Update "Last Contacted" dates automatically from Gmail/Calendar metadata without requiring a manual `Activity` file.
2.  **Relationship Velocity:** Transition from "Recency-only" scoring to "Interaction Velocity" (detecting when a deal is "heating up").
3.  **Account-Level Health:** Aggregate scores from multiple contacts to determine the overall strength of a corporate/VC relationship.
4.  **Autonomous Matchmaking:** Programmatically suggest "Warm Matches" between your Deal Inventory and Investor Accounts.

## 3. Functional Requirements

### 3.1 The "Shadow Log" (Passive Telemetry)
*   **Feature:** `interactions.json` State File.
*   **Requirement:** The `sync-workspace` skill must maintain a hidden state file in `crm-data/staging/interactions.json`.
*   **Logic:** Every time a sync runs, it maps *every* email address seen to a `last_interaction_date`, regardless of whether a formal `Activity` is created.
*   **Benefit:** Warmth scores are accurate even if you are too busy to log notes.

### 3.2 Relational Graphing (Account Aggregation)
*   **Feature:** Multi-Contact Health Aggregation.
*   **Requirement:** The `intelligence-engine.py` must calculate an `account-warmth` score.
*   **Logic:** `Account Score = Average(Warmth of all linked Contacts) + (Bonus for Quantity of Contacts)`.
*   **Benefit:** You can see which VC firms you are truly "deep" in, versus just knowing one person.

### 3.3 Vector Warmth (Velocity Engine)
*   **Feature:** `velocity-score` Metadata.
*   **Requirement:** Track interactions over a rolling 7-day window.
*   **Logic:** 
    *   **High Velocity:** >3 interactions in 7 days (Flag as "🔥 HOT").
    *   **Stable:** 1 interaction in 14 days.
    *   **Atrophying:** Score is high but velocity is 0 for 21+ days.
*   **Benefit:** Proactively surfaces deals that are losing momentum before they go "Cold."

### 3.4 The Brokerage Matchmaker
*   **Feature:** `COMPATIBILITY.md` suggestions.
*   **Requirement:** A script to compare `Deals/*.md` against `Accounts/*.md`.
*   **Logic:** Match `Deal:sector` to `Account:investment-mandate` AND `Deal:target-raise` to `Account:check-size`.
*   **Output:** List top 5 suggested "Warm Introductions" on the dashboard.

## 4. Technical Specifications
*   **Data Structure:** Extend YAML frontmatter to include `velocity-score` and `account-warmth-index`.
*   **State Management:** `interactions.json` acts as a local cache to prevent redundant API calls to Gmail.
*   **Processing:** Enhance `intelligence-engine.py` to handle the graph math (linking contacts to accounts via Wikilink parsing).

## 5. User Stories
*   **As a Broker:** "I want to open my dashboard and see which 3 investors are currently 'Hot' so I can prioritize sending them my newest deal today."
*   **As an Advisor:** "I want my CRM to automatically tell me I haven't spoken to *anyone* at Example Bank in 30 days, even if I haven't logged a specific activity."
