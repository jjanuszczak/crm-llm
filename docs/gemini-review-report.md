# Gemini Review Report

## Scope Covered
`GEMINI.md`, `.gemini/settings.json`, `.gemini/skills/*`, `.gemini/skills/**/scripts/*`, `README.md`, `scripts/*`.

## Summary
This repo is the logic layer for a private CRM data vault, with Gemini CLI skill definitions in `.gemini/skills/` and automation scripts in `scripts/`. The operational mandates in `GEMINI.md` are clear and largely consistent with the skills. There are a few gaps between README claims and actual skills, plus a couple of likely schema and data-quality issues.

## Gemini Config
- Settings hooks auto-load a vault tree and `GEMINI_INDEX.md` on session start. This assumes `CRM_DATA_PATH` points to a valid vault and that `tree` exists. (`.gemini/settings.json`)
- The project-level instructions live in `GEMINI.md` (uppercase). There is no lowercase `gemini.md`. (`GEMINI.md`)

## Skills Inventory (from `.gemini/skills/`)
- Creation: `create-account`, `create-contact`, `create-deal`, `create-opportunity`, `create-activity`, `create-task`, `create-daily-report`.
- Operations: `update-dashboard`, `manage-intelligence`, `sync-workspace`, `sync-google-tasks`, `init-crm-data`.
- Supporting scripts: `update-dashboard/scripts/update-dashboard.py`, `init-crm-data/scripts/init-vault.py`, `sync-google-tasks/scripts/sync-tasks.py`.

## Findings (ordered by severity)
1. Missing Skill vs README: README advertises a `matchmaker` skill but no skill definition exists under `.gemini/skills/`. The script exists at `scripts/matchmaker.py`, but there’s no skill wrapper. This is a functional/documentation mismatch. (`README.md`, `scripts/matchmaker.py`, `.gemini/skills/*`)
2. Likely Frontmatter Bug: `create-contact` specifies `full--name` (double hyphen) in frontmatter. That’s probably a typo and would create inconsistent schemas across contacts. (`.gemini/skills/create-contact/SKILL.md`)
3. Hardcoded Insights in Dashboard: `update-dashboard.py` uses a static list of “insights” unrelated to actual data, and only partially uses activity data. This risks stale or incorrect executive summaries in `DASHBOARD.md`. (`.gemini/skills/update-dashboard/scripts/update-dashboard.py`)
4. YAML Parsing Limitations: `update-dashboard.py` parses frontmatter manually and only handles a single list key (`investment-mandate`). Any other list fields or nested YAML won’t parse correctly. This can silently drop data. (`.gemini/skills/update-dashboard/scripts/update-dashboard.py`)

## Notable Alignments
- Automatic bookkeeping (commit in data repo) is reinforced in both `GEMINI.md` and several skill definitions.
- `update-dashboard` also runs `matchmaker.py` and `intelligence-engine.py`, aligning with the “Intelligence Loop” in `GEMINI.md`. (`GEMINI.md`, `.gemini/skills/update-dashboard/scripts/update-dashboard.py`, `scripts/intelligence-engine.py`)

## Recommendations
1. Add a `matchmaker` skill definition or update `README.md` to match reality.
2. Fix `full--name` to `full-name` in `create-contact` to avoid schema drift.
3. Replace static insights in `update-dashboard.py` with actual synthesis or remove them if not ready.
4. Consider switching frontmatter parsing to a YAML parser for reliability.

