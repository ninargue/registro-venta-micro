---
name: lifecycle-dev
description: Manages the full lifecycle of a branch in this repo: create the branch from an issue with its worktree, VS Code workspace entry, initial commit and draft PR, and later merge the PR and clean up worktree and branches. Use it whenever the user wants to start work on an issue ("crear rama", "nueva rama", "iniciar issue", "nueva feature", "start issue", "new branch"), while developing it (commits, PR description, review) or to finish one ("mergear PR", "cerrar rama", "terminar rama", "limpiar rama", "merge PR", "cleanup branch"), even if they don't name the skill.
---

# Lifecycle Dev

Covers the whole life of an issue, in three flows: **Create** (issue → branch → worktree → initial commit → draft PR), **Develop** (atomic commits → PR description → adversarial review) and **Cleanup** (PR ready → merge → issue check → worktree and branch cleanup).

## Sources of truth

This skill only adds what the repo docs don't cover: worktrees, the VS Code workspace, and agent-specific steps and pitfalls. For everything else, read the canonical source at the start of each flow and follow it. Don't copy its rules into this file: if they change there, this skill must not go stale.

| Topic | Canonical source |
|---|---|
| Branch types, naming rules, source and target branch | `.github/CONTRIBUTING.md` → *Convención de nombres de branch* |
| Exact branch-name regex | `.github/workflows/branch-policy.yml` |
| Commit and PR title format, scopes | `.github/CONTRIBUTING.md` → *Convención de commits*; `CLAUDE.md` |
| Labels (`sin-changelog`, `breaking-change`, …) | `.github/CONTRIBUTING.md` → *Etiquetas* |
| Work cycle: draft PR, update branch, self-review, merge strategy | `.github/CONTRIBUTING.md` → *Ciclo de trabajo* |
| Release, hotfix, changelog, tag, backport | `.github/CONTRIBUTING.md` → the matching subsections |
| PR body | `.github/pull_request_template.md` and `.github/PULL_REQUEST_TEMPLATE/` |
| Commit rules: checks, staging, push | `commit` skill |
| Other agent rules | `CLAUDE.md` |

If this skill and those sources disagree, the sources win. Point out the mismatch to the user so the skill can be fixed.

Skill-only conventions:
- **Worktree:** a sibling of the **main repository** (not of the current worktree): `<parent of main repo>/wt-<issue_number>-<short-description>`. Mandatory for every branch, so parallel work never mixes in one checkout. `git rev-parse --show-toplevel` returns the current worktree when run inside one, so get the main repo from the shared git dir instead:
  ```bash
  main_repo="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
  parent="$(dirname "$main_repo")"
  ```
- **VS Code workspace:** `<parent of main repo>/opma-projects.code-workspace`. Skip it if it doesn't exist.
- **Reviewers:** none. Use `--assignee @me` only.
- **Temp files:** the session scratchpad, or `mktemp`. Never `/tmp` (Windows / Git Bash).

---

## CREATE FLOW

### 1 — Gather context

Run in parallel: resolve `main_repo` and `parent` (see above), `git status --short`, `gh auth status`. Read the CONTRIBUTING sections on branches and commits.

Ask the user, in one go:
1. **Issue number.** Fetch it with `gh issue view <n> --json number,title,body,url,labels`. If there is no issue, offer to create one with `gh issue create` and the matching template from `.github/ISSUE_TEMPLATE/`.
2. **Type and scope.** Suggest both from the issue's labels and content.

The source branch follows from the type, per CONTRIBUTING.

### 1.5 — Refine the requirement (optional, user's choice)

Look for skills available in this session that refine a requirement: a requirement-enrichment skill (e.g. `enrich-requeriments`) or a spec-driven development (SDD) cycle. If at least one exists, ask the user which to use, listing each one found plus "none". Never pick one yourself. If none is available, skip this step without mentioning it.

Run the chosen skill on the issue, then offer to post its result with `gh issue comment <n> --body-file <file>`.

### 2 — Branch name

Derive the name from the issue title, following CONTRIBUTING → *Convención de nombres de branch*. Prefix the description with the issue number (`<type>/<issue_number>-<description>`), as that section allows. Read the regex from `branch-policy.yml` and check the name with `grep -qE` before proposing it, because a bad name only shows up once the PR fails. Let the user accept or change it.

### 3 — Branch and worktree

```bash
git fetch origin --prune
git branch <branch-name> origin/<source-branch>
git worktree add "<worktree-path>" <branch-name>
```

Branch from `origin/<source-branch>`, not the local copy, which may be stale. If the branch or the path already exists, stop and ask. From here on, run every command from inside the worktree.

Add the worktree to the VS Code workspace: read the file and use the Edit tool to append `{ "path": "<worktree-path>" }` to `folders`, matching the style of the existing entries. Skip this if the folder is already listed.

### 4 — Initial commit and push

An empty commit lets the draft PR open right away (CONTRIBUTING: draft PR at the first commit):

```bash
git commit --allow-empty -m "<type>(<scope>): inicia <issue-title-lowercase>" -m "Refs #<issue_number>"
git push -u origin <branch-name>
```

This initial push needs no confirmation: the `commit` skill exempts it from the push rule. Every later push does.

If a husky hook fails, show the output and fix the cause. Never use `--no-verify`.

### 5 — Draft PR

Fill in the PR template from the issue: copy acceptance criteria verbatim, add `Closes #<n>`, tick type and base. Leave the checklist for self-review. Write the body to a temp file, then:

```bash
gh pr create --draft --base <source-branch> --head <branch-name> \
  --title "<title per commit convention>" --body-file "<body-file>" --assignee @me
```

### 6 — Summary

```
Rama      : <branch-name>  (desde origin/<source-branch>)
Worktree  : <worktree-path>
VS Code   : workspace actualizado | omitido
PR        : <pr-url>  [Draft · base: <source-branch>]
Issue     : <issue-url>
```

---

## DEVELOP FLOW

Runs inside the worktree, from the draft PR until the issue's development is complete.

### D1 — Atomic commits

Split the work into atomic commits: each one holds a single logical change, leaves the code working (checks pass) and can be reverted on its own. Don't mix unrelated changes, and don't save everything for one final commit.

When a logical change is ready, propose the commit to the user (files and message) and wait for confirmation. Never commit on your own initiative. Once confirmed, make it with the `commit` skill. Pushing still needs its own confirmation, per the `commit` skill.

### D2 — Close the development of the issue

When every acceptance criterion is covered and the user confirms the development is done:

1. Update the draft PR's body with a complete description of the changes: `gh pr edit <n> --body-file <file>`, following the PR template.
2. Run the `adversarial-reviewer` subagent on the whole PR, passing the PR number, the issue number and the spec path if there is one. This happens only here, once development is finished, never after each commit or push. If its findings lead to more commits, don't rerun it unless the user asks. It writes its report to `docs/reviews/` (git-ignored) and returns the path.
3. Reply only with the PR URL and the review report path. Don't repeat the summary in chat: the session will be lost, the PR won't.

The PR then moves to the Cleanup flow once the user asks to merge it.

---

## CLEANUP FLOW

Read CONTRIBUTING → *Ciclo de trabajo* (and *Release*, *Hotfix* or *Backport* when the base is `master`). Resolve the PR:

```bash
gh pr view <n> --json number,headRefName,baseRefName,state,isDraft,mergeStateStatus,body,url
git worktree list
```

### C1 — Preconditions

- **Worktree clean:** `git -C <worktree-path> status --short`. If there are changes, stop and ask. Never discard them.
- **Self-review done:** confirm with the user, then `gh pr ready <n>` if it's still a draft.
- **Up to date with the base:** if `mergeStateStatus` is `BEHIND`, update as CONTRIBUTING describes (`gh pr update-branch <n>` does the same as the *Update branch* button). Dependabot PRs are the exception: comment `@dependabot rebase`, because a manual update makes Dependabot stop maintaining the PR.
- **Required checks green:** `gh pr checks <n> --watch --required --fail-fast`. After an update the checks rerun on the new commit, and merging before they finish fails with `Required status check "..." is expected`.

### C2 — Merge

Use the strategy CONTRIBUTING gives for that base, and confirm with the user before running `gh pr merge <n> --squash|--merge`. Don't pass `--delete-branch`: it tries to delete the local branch, which the worktree still uses. Merge before removing the worktree, so a failed merge still leaves a working checkout.

### C3 — Check the issue

Compare each acceptance criterion in the issue with what the PR delivered. Create follow-up issues for anything missing, then post on the issue (even if `Closes #` already closed it) with `gh issue comment <n> --body-file <file>`, using the sections `## Verificación de criterios de aceptación`, `## Cambios adicionales (fuera de alcance)` and `## Pendientes derivados`.

### C4 — Remove the worktree and branches

```bash
git worktree remove <worktree-path>   # never --force; if it refuses, report and ask
git fetch origin --prune               # GitHub already deleted the remote branch
```

Remove the worktree's entry from the VS Code workspace with the Edit tool.

Local branch: after a **squash** merge, `git branch -d` fails with "not fully merged", because the squashed commit has a different SHA. Confirm the PR shows `state: MERGED`, then use `git branch -D <branch-name>` and say why. After a **merge commit**, use `-d`; if it fails, stop and ask.

### C5 — Release / hotfix (base `master`)

Follow CONTRIBUTING → *Tag y release en GitHub* and *Backport a `develop`*. Confirm the version with the user before tagging.

### C6 — Summary

```
PR        : <pr-url>  (merged · <estrategia>)
Issue     : #<n>  comentario de verificación publicado
Worktree  : eliminado  (<worktree-path>)
VS Code   : workspace actualizado | omitido
Rama      : local eliminada, remota eliminada por GitHub
```
