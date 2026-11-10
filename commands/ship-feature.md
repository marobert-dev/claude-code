---
description: From `dev`, branch to feature/*, commit, push, open a PR into dev, merge it, return to dev and delete the feature branch (remote + local)
argument-hint: [short description of the work | branch-name]
allowed-tools: Bash(git:*), Bash(gh:*), AskUserQuestion
---

You run the full feature-branch cycle in one pass: branch, commit, push, pull request, merge, clean up. Invoking this command is the user's explicit request for every commit, push, PR and merge below, but only into `dev`. Nothing here ever touches `main`.

Hard rules, no exception and no override by arguments:
- The PR base is always `dev`. Never push to, merge into, or open a PR against `main`.
- Never delete `main` or `dev`, locally or on the remote.
- Never use `--force`, `--admin`, `git branch -D`, `--no-verify`, or `git add -A` / `git add .`.

Do not use heredocs or `python -`: a hook blocks commands that wait on stdin. Pass commit messages with repeated `-m` flags and PR bodies with a quoted `--body` string.

`$ARGUMENTS` is an optional description of the work or a branch name. If empty, derive both from the diff.

## 1. Preflight

Run in one call: `git branch --show-current`, `git status --short`, `gh auth status`.

| Current branch | Action |
|---|---|
| `dev` | Go to step 2. |
| `feature/*` | Reuse it: skip the branch creation in step 2 and set `<feature>` to it. |
| anything else (including `main`) | Stop. Say the command starts from `dev` and name the current branch. |

Stop if `gh` is not authenticated or `git status` shows nothing to commit on a fresh branch from `dev`. Stop on unresolved merge conflicts.

## 2. Branch

Run `git pull --ff-only origin dev`. If it fails, stop and report; do not merge or rebase on the user's behalf.

Name the branch `feature/<kebab-case-summary>`: lowercase, 2 to 5 words, describing the change (existing examples: `feature/pm-bookkeeping-script`, `feature/block-stdin-python-hang`). If the name already exists locally or on `origin`, stop and ask for another.

Run `git checkout -b <feature>`. Uncommitted work comes along.

## 3. Commit

Stage by explicit path, never wholesale. The working tree often holds unrelated files (binaries, scratch work, generated output) that must not ship.

1. Read `git status --short` and `git diff --stat`.
2. Stage the files that belong to the described work with `git add <path> ...`.
3. If some changes clearly do not belong or you cannot tell, ask with AskUserQuestion which to include. Leave unselected files untouched.
4. Skip anything that looks like a secret (`.env`, credentials, tokens, keys) and say so.

Write the message in English, imperative, one subject line under 72 characters, no type prefix, matching the repo history (`Block commands that hang on stdin in three layers`). Add a short body with `-m` only when the why is not obvious from the subject. Append the commit attribution line the session instructions require.

If a pre-commit hook fails, fix the cause, re-stage, and make a new commit. Do not bypass or amend.

## 4. Push

`git push -u origin <feature>`

## 5. Pull request

`gh pr create --base dev --head <feature> --title "<commit subject>" --body "<body>"`

Body: a short summary of what changed and why, as bullets. Append the pull request attribution line the session instructions require. Capture the PR number from the printed URL.

## 6. Merge

`gh pr merge <number> --merge`

Use a merge commit: the repo history shows `Merge pull request #N`. Do not pass `--delete-branch`; cleanup is explicit in step 7 so each part is verified.

If the merge is blocked (failing or pending required checks, conflicts, review required), stop. Report the PR URL and the reason, and leave the branch and PR as they are. Do not retry with `--admin` or any bypass.

## 7. Return to dev and clean up

Run in order, stopping at the first failure:

1. `git checkout dev`
2. `git pull --ff-only origin dev`
3. `git branch -d <feature>`: the safe delete. If git refuses because the branch looks unmerged, stop and report; do not escalate to `-D`.
4. If `git ls-remote --heads origin <feature>` prints a line, run `git push origin --delete <feature>`. GitHub may already have auto-deleted it.
5. `git fetch --prune`

Finish with `git status --short` and `git branch -a` to confirm the state.

## 8. Report

Short bullets: branch name, commit subject, PR URL and number, merge result, final branch (`dev`), confirmation that the local and remote feature branches are gone. Mention any file left unstaged on purpose. If you stopped early, state which step failed, the exact error, and what state the repo and PR are in now.
