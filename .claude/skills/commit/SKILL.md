---
name: commit
description: Creates a Conventional Commit in this repo after running the relevant checks and showing their output. Use it only when the user explicitly asks for a commit ("commitea", "haz commit", "commit") or confirms one proposed by the lifecycle-dev skill. Never commit on your own initiative.
---

# Commit

## Sources of truth

Read these before committing; don't copy their rules here, so this skill doesn't go stale:

| Topic | Canonical source |
|---|---|
| Message format, types, scopes, breaking changes | `.github/CONTRIBUTING.md` → *Convención de commits*; `CLAUDE.md` |
| Which checks apply to which layer | `.husky/pre-push` (backend and frontend steps) |

If this skill and those sources disagree, the sources win. Tell the user so the skill can be fixed.

## Steps

1. **Review the change.** Run `git status --short` and `git diff` (plus `git diff --staged`). Identify the files that belong to this change and leave out unrelated ones. If anything is ambiguous, ask.

2. **Run the checks.** For each layer touched (`backend/`, `frontend/`), run the same steps `.husky/pre-push` runs for that layer. Read them from the hook so the list stays current. If only docs or config changed, say there's nothing to check and why. Show the user a short summary of the output (pass/fail per step, plus the error if one failed). If a check fails, stop and fix the cause. Never disable a lint or type rule to make it pass.

3. **Stage only this change's files:** `git add <file> ...`. Never use `git add .` or `-A`.

4. **Write the message** following the canonical convention: type, scope when it applies, lowercase imperative description. Add a body only when the *why* isn't obvious, and add `Refs #<n>` when there's an issue.

5. **Commit:** `git commit -m "<subject>" [-m "<body>"]`. The husky pre-commit hook runs lint-staged and may reformat files. If it fails, show the output, fix the cause, and create a new commit. Never use `--no-verify`, and don't amend unless the user asks.

6. **Report** the commit hash and subject (`git log --oneline -1`). 

## Push

Never run `git push` until the user explicitly confirms it, every time. This skill is the canonical source for that rule. The only exception is the initial push that creates a new branch on the remote, in the `lifecycle-dev` Create flow.
