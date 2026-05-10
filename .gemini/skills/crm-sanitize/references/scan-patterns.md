# Scan Patterns

Use these as starting points. Tune patterns to the specific audit request and avoid dumping large sensitive matches into the final answer.

## Baseline Repo Checks

```bash
git status --short --ignored
git ls-files crm-data
git log --all --oneline -- crm-data '*DASHBOARD.md' '*RELATIONSHIP_MEMORY.md' '*INTELLIGENCE.md'
find crm-data -maxdepth 2 -type f | sed -n '1,120p'
```

`find crm-data` confirms local private data exists and stays outside tracked files. Do not inspect private contents unless the task requires it.

## Email Addresses

```bash
git grep -n -I -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
git grep -n -I -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' $(git rev-list --all)
```

Expected safe matches may include `example.com`. Treat operator emails, Gmail addresses, and customer/counterparty domains as sensitive.

## Workspace Provenance And Staging

```bash
git grep -n -I -E 'gmail|googleusercontent|drive\.google|docs\.google|calendar\.google|source-ref|message-id|thread-id|granola|crm-data/staging'
git grep -n -I -E 'DASHBOARD|RELATIONSHIP_MEMORY|INTELLIGENCE|workspace_sync_state|activity_updates|contact_discoveries|lead_decisions|task_suggestions|granola_updates'
```

This scan catches copied staging output, source refs, and derived CRM artifacts.

## CRM Record Paths

```bash
git grep -n -I -E 'Activities/[0-9]{4}|Tasks/[0-9]{4}|Opportunities/[A-Z]|Contacts/[A-Z]|Organizations/[A-Z]|Deal-Flow/[A-Z]|Leads/[A-Z]' -- ':!examples/**'
```

Synthetic paths in `examples/` can be acceptable if they use anonymized names.

## Known Private-Looking Terms

When a prior audit identifies specific names, build a single alternation and scan both current tree and history:

```bash
git grep -n -I -E '<term1>|<term2>|<term3>'
git grep -n -I -E '<term1>|<term2>|<term3>' $(git rev-list --all)
```

Keep this list narrow enough to avoid false positives like protocol names, standards, or generic words.

## Metadata

```bash
git log --all --format='%an <%ae>%n%cn <%ce>' | sort -u
```

If private emails must be scrubbed from history, rewrite author and committer metadata too.
