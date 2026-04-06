# Skill: CRM Create Lead

## Description
Creates and manages first-class `Lead` records using the current lead lifecycle. This skill is backed by [lead_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/scripts/lead_manager.py).

## Usage
- `crm-create-lead --name "Jane Doe - Example Capital" --person-name "Jane Doe" --company-name "Example Capital"`
- `lead-set-status "Jane-Doe-Example-Capital" --status engaged`
- `lead-convert "Jane-Doe-Example-Capital" --opportunity-name "Example Capital - Strategic Advisory - 2026"`

## Workflow

1. Resolve `CRM_DATA_PATH`.
2. Use [lead_manager.py](/Users/johnjanuszczak/Projects/crm-logic/.gemini/skills/crm-lead-manager/scripts/lead_manager.py) for creation, status updates, validation, revival, and conversion.
3. Support sparse early leads, but require `person-name` and `company-name` before moving to `qualified`.
4. On conversion, carry provenance and linked records forward into:
   * `Organization`
   * `Contact`
   * `Account`
   * `Opportunity`

## Notes

- Prefer Leads over premature direct creation of Contact + Account + Opportunity when the relationship is still early.
