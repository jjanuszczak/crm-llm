---
name: crm-sanitize
description: Scan the crm-logic repository for private CRM data leakage and guide conservative sanitization. Use when asked to audit, scrub, anonymize, remove from Git history, or verify that private vault data, real CRM counterparties, personal emails, source refs, staging outputs, or migration artifacts have not slipped into tracked repo content or reachable Git history.
---

# CRM Sanitize

## Overview

Use this skill to keep `crm-logic/` public-friendly while protecting private CRM data in `CRM_DATA_PATH`. The default posture is audit-first: report findings and apply current-tree sanitization when unambiguous; rewrite Git history only when the user explicitly asks for it or confirms the risk.

## Core Rules

- Treat `crm-data/` as private even when ignored.
- Do not print sensitive file contents unless the user needs specific evidence; prefer file paths, line numbers, and short labels.
- Do not edit vault records as part of repo sanitization.
- Prefer anonymized examples such as `Example Company`, `Example Bank`, `Jane Doe`, `operator@example.com`, and `Example-Company-Strategic-Advisory-2026`.
- Before history rewriting, ensure the working tree is clean or intentionally staged/committed.
- After history rewriting, remove backup refs, expire reflogs, run garbage collection, and force-push only with explicit leases.

## Audit Workflow

1. Confirm repo state:

```bash
git status --short --ignored
git branch --show-current
git log --oneline --decorate -5
```

2. Confirm the vault is ignored and not tracked:

```bash
git ls-files crm-data
git log --all --oneline -- crm-data '*DASHBOARD.md' '*RELATIONSHIP_MEMORY.md' '*INTELLIGENCE.md'
```

3. Scan tracked current-tree content:

```bash
git grep -n -I -E '<pattern>'
```

Use [references/scan-patterns.md](references/scan-patterns.md) for pattern categories and examples.

4. Scan reachable Git history when the user asks for history assurance:

```bash
git grep -n -I -E '<pattern>' $(git rev-list --all)
git log --all --oneline -- <suspicious-path>
git log --all --format='%ae%n%ce' | sort -u
```

5. Classify findings:

- **Critical:** tracked vault records, staging JSON with real Workspace data, API tokens, personal email addresses, raw source refs, real CRM activities/tasks/notes.
- **High:** real contact/company/opportunity names in docs, skills, scripts, templates, tests, or examples.
- **Medium:** private-looking business context in archived docs, migration helpers, hardcoded dashboards, report examples.
- **Low:** synthetic examples, generic domains, placeholder data.

## Current-Tree Sanitization

For clear findings:

- Replace real names with anonymized examples.
- Move operator emails and private identifiers to `crm-data/settings.json`, `.env`, or documented local configuration.
- Delete obsolete migration helpers that encode private slugs.
- Update references when deleting a tracked file.
- Run tests after code changes:

```bash
uv run python -m unittest discover -s tests
```

## History Rewrite

Read [references/history-rewrite.md](references/history-rewrite.md) before rewriting history.

Only rewrite when:

- the user explicitly asks to remove findings from history, or
- the finding is severe enough that current-tree cleanup is insufficient and user approval is clear.

Use `git filter-repo` when available. If unavailable, use built-in `git filter-branch` carefully with `LC_ALL=C LANG=C` and explicit cleanup.

After rewriting, verify:

```bash
git grep -n -I -E '<pattern>' $(git rev-list --all)
git log --all --oneline -- <deleted-sensitive-path>
git log --all --format='%ae%n%ce' | sort -u
uv run python -m unittest discover -s tests
```

## Reporting

Return:

- what was scanned
- what was found
- what was changed
- whether history was rewritten
- verification commands and results
- remaining risks, especially GitHub unreachable object/cache retention

If history was force-pushed, include the new remote ref SHAs and warn collaborators that they must rebase or reclone.
