# History Rewrite

History rewriting is disruptive. Prefer current-tree sanitization unless the user asks for history removal or the finding is severe.

## Before Rewriting

1. Confirm the target branches:

```bash
git branch -a
git show-ref
git log --oneline --decorate -5
```

2. Ensure all desired current-tree sanitization is committed.

3. Record the current remote SHAs for explicit leases:

```bash
git ls-remote origin main issue-29-web-crm-dashboard-mvp
```

Use network escalation if the sandbox cannot resolve GitHub.

## Preferred Tool

Use `git filter-repo` if installed:

```bash
git filter-repo --replace-text replacements.txt --refs main issue-29-web-crm-dashboard-mvp
```

Use `git filter-branch` only when `git filter-repo` is unavailable.

## Built-In Fallback

Use plain C locale to avoid locale failures:

```bash
LC_ALL=C LANG=C FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --force --tree-filter '<tree-filter-command>' -- --all
```

For metadata email rewrite:

```bash
LC_ALL=C LANG=C FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --force --env-filter '<env-filter-command>' -- --all
```

Prefer exact replacements. Avoid broad patterns that can corrupt valid technical strings such as `RFC 3339`.

## Cleanup

Filter-branch creates backup refs that keep old commits reachable. Remove them, expire reflogs, and garbage collect:

```bash
git for-each-ref --format='%(refname)' refs/original | xargs -n 1 git update-ref -d
git reflog expire --expire=now --expire-unreachable=now --all
git gc --prune=now --aggressive
```

Check for linked worktrees that may still point at old commits:

```bash
git worktree list --porcelain
```

Remove clean temporary detached worktrees when they retain pre-sanitized commits:

```bash
git worktree remove /path/to/worktree
git worktree prune
```

## Verification

Run current-tree and all-history scans:

```bash
git grep -n -I -E '<pattern>'
git grep -n -I -E '<pattern>' $(git rev-list --all)
git log --all --oneline -- <deleted-sensitive-path>
git log --all --format='%ae%n%ce' | sort -u
uv run python -m unittest discover -s tests
```

No output from `git grep` means no matches. Exit code `1` from `git grep` is expected when no matches exist.

## Force Push

Use explicit leases, not blind force:

```bash
git push \
  --force-with-lease=main:<old-main-sha> \
  --force-with-lease=issue-29-web-crm-dashboard-mvp:<old-branch-sha> \
  origin main issue-29-web-crm-dashboard-mvp
```

Verify:

```bash
git ls-remote origin main issue-29-web-crm-dashboard-mvp
```

## Caveats

- GitHub may retain unreachable objects, caches, forks, or PR refs outside normal branch history.
- For maximum assurance, ask GitHub Support to purge cached/unreachable sensitive objects.
- Collaborators must rebase, reset, or reclone after force-pushed history rewrites.
