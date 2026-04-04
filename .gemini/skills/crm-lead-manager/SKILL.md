# Skill: CRM Lead Manager

## Description
Manages lead lifecycle decisions in the CRM using a relationship-first model. Use this skill when the user wants to create, update, validate, revive, or convert a `Lead`, or when they want guidance on whether a person or organization should still be a `Lead` versus a `Contact`, `Organization`, `Account`, or `Opportunity`.

This skill reflects the current intended lifecycle:
- `new`: identified entity, not yet meaningfully engaged
- `engaged`: a known contact exists and there has been real interaction
- `qualified`: contact and organization are known, and there is intent to explore work together
- `converted`: the lead has been resolved into durable CRM records

This skill also distinguishes multiple conversion outcomes:
- commercial opportunity path: `Organization + Contact + Account + Opportunity`
- relationship-only path: `Organization + Contact`

Current implementation support now covers both lead status management and two conversion modes:
- `commercial`
- `relationship-only`

## When To Use
- A new person or company has been identified and should be tracked before full CRM conversion.
- The user wants to decide whether a lead should be `new`, `engaged`, or `qualified`.
- The user wants to validate whether a lead is ready for qualification.
- The user wants to revive a disqualified lead.
- The user wants to convert a lead and needs the correct conversion path.
- The user wants to check whether the current script behavior matches the intended operating model.

## Workflow

1. **Classify the relationship**
   - Determine whether this is a commercial lead, a deal-related lead, a partner, a supplier, or another relationship type.
   - If the user is unsure, default to asking: "What durable records should exist after conversion?"
   - Read [references/lifecycle.md](references/lifecycle.md) when you need the canonical stage definitions and conversion logic.
   - Read [references/flowchart.md](references/flowchart.md) when you want a visual decision flow.

2. **Choose the right lead stage**
   - `new`: there is an identified person or organization, but no meaningful engagement yet.
   - `engaged`: there is a real contact and at least one concrete interaction such as an email, call, or meeting.
   - `qualified`: contact and organization are both known, and there is a credible path to work together.
   - `converted`: only after durable records have been created and linked.

3. **Use the current script where it fits**
   - The operative implementation is [scripts/lead_manager.py](scripts/lead_manager.py).
   - Use it for:
     - lead creation
     - status updates
     - qualification readiness checks
     - revival from `disqualified`
      - conversion to `Organization + Contact + Account + Opportunity`
     - conversion to `Organization + Contact`
   - Read [references/cli-patterns.md](references/cli-patterns.md) for command patterns.

4. **Respect current qualification rules**
   - Current script requirement for `qualified`:
     - `person-name` must exist
     - `company-name` must exist
   - This matches the intended model well enough for now and should be treated as the operational gate.

5. **Handle conversion by use case**
   - If the user is pursuing a commercial relationship or active work stream, use the commercial opportunity path.
   - If the lead is better modeled as a deal, partner, supplier, or another non-opportunity relationship, do not force an `Account` or `Opportunity` unless there is a real commercial workflow that needs them.
   - If the user requests relationship-only conversion, use `--conversion-mode relationship-only`.

6. **Carry forward relationship history**
   - On commercial conversion, preserve provenance back to the lead.
   - Existing lead-linked `Notes` and `Activities` should be copied onto the new `Opportunity`.
   - Existing open lead-linked `Tasks` should be moved to the new `Opportunity`.
   - This behavior is already implemented in the current script.

7. **Explain the result clearly**
   - Tell the user which stage the lead is in and why.
   - Tell the user which conversion path was used or intended.
   - If the current implementation cannot support the intended path, say so explicitly and point to the enhancement gap.

## User-Facing Usage

The user can ask for:
- "Create a new lead for Jane at Example Capital."
- "Move this lead to engaged."
- "Check if this lead is ready to qualify."
- "Revive this disqualified lead."
- "Convert this lead into an account and opportunity."
- "This lead is really a supplier relationship; convert it without creating an opportunity."
- "Does this lead belong in Leads or should it already be an Organization and Contact?"

When acting, prefer the current CLI for supported flows:
- `python3 scripts/lead_manager.py create ...`
- `python3 scripts/lead_manager.py set-status ...`
- `python3 scripts/lead_manager.py validate-qualified ...`
- `python3 scripts/lead_manager.py revive ...`
- `python3 scripts/lead_manager.py convert ...`

## Current Implementation Notes
- Current status rules and conversion logic live in [scripts/lead_manager.py](scripts/lead_manager.py).
- The compatibility wrapper remains at [../../../../scripts/lead_manager.py](../../../../scripts/lead_manager.py) so existing imports and older commands still work.
- The skill-owned script is the canonical implementation.
