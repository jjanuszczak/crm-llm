# Skill: CRM Create Daily Report

## Description
Writes a concise daily progress report for the current session into `CRM_DATA_PATH/Reports/`. Use this after a substantial `crm-daily-processing` run when the user wants a durable written report.

## Usage
`crm-create-daily-report`

## Workflow

1. Review the current session only.
2. Summarize:
   * material relationship work
   * CRM mutations
   * emails sent / logged
   * task and opportunity state changes
   * key open items
3. Resolve `CRM_DATA_PATH` and ensure `Reports/` exists.
4. Use [report-template.md](/Users/johnjanuszczak/Projects/crm-logic/templates/report-template.md).
5. Save as `YYYY-MM-DD - Progress Report.md`.
6. Do not auto-commit unless the user explicitly wants a commit.

## Notes

- This is a reporting skill, not a top-level daily workflow. The top-level workflow is `crm-daily-processing`.
