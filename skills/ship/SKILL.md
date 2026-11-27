---
name: ship
description: Commit a finished change and, when asked, push it and open a PR, with evidence. Runs the checks fresh (full for a built feature, targeted otherwise) and makes sure the change was reviewed. Stages only this conversation's files, never other sessions' work. Writes a commit message that explains why, and a PR body with the acceptance-criteria table, test evidence, migrations, blast radius, whether it can be undone, and rollback steps. It never pushes to main/master or force-pushes, and asks before anything leaves the machine. Use only when the user explicitly asks to commit, ship, push or open a PR.
disable-model-invocation: true
---

# Ship

Get a verified change into git, and out of the machine if asked, so a reviewer can trust it without redoing the work. Committing, pushing and opening a PR happen only because the user asked for them in this conversation (`AGENTS.md` §1). Each step that leaves the machine needs its own yes.

Read the project profile first. It says which branch is the base, what pushing to a branch triggers (in some projects, pushing to `main` deploys production), and the known baseline failures.

## 1. Preconditions

- **The user asked** to commit, push or open a PR. If they only asked to commit, stop after step 4.
- **The change was reviewed:** `review-change` ran on it with no must-fix findings left, or the user explicitly waived the review. If neither, run it now.
- **Checks, fresh:** run them now, even if they ran earlier. For a feature built with `build-feature`, that's the full suite (`~/agent-workflow/bin/run-checks`); for anything else, the tests of the modules the change touches (`AGENTS.md` §4). New failures (not on the profile's baseline list) block shipping. Report them, and don't commit unless the user decides otherwise with the failures in front of them.

## 2. Branch

- Never commit straight to `main`/`master` or the profile's base branch unless the user explicitly asked for that, and never push to them yourself. The `guard-commands` hook blocks the push anyway.
- If you're on the base branch, create a feature branch (`git switch -c <prefix><slug>`, using the project's or the user's branch prefix if there is one). Creating a branch keeps the working tree as it is.

## 3. Stage only this change

Another session may share this checkout. Never `git add -A` or `git add .`.
- List the files this conversation created or changed, plus files the user explicitly asked to include. Show the list.
- Stage them by path: `git add -- <files>`. If a file also holds someone else's edits, tell the user instead of committing them.
- Check `git diff --cached --stat` against the list. Nothing else should be staged.
- Make sure nothing secret, large or generated is staged: `.env` files, credentials, data exports, build output.

## 4. Commit

The message explains the change for someone reading `git log` in a year:
- Subject: imperative, at most about 70 characters, says what changes for the user or the system.
- Body: why the change was needed, what it does at a high level, the acceptance criteria it covers (`AC1–AC5`), ADRs it adds or follows, and anything a reviewer should know (a migration, a feature flag, a known limitation).
- End with the attribution lines your harness requires, if any.

## 5. Push and PR (only when asked)

1. Ask before pushing: branch name, remote, and what the push triggers (CI, a preview deploy). Push with `git push -u origin <branch>`, never with `--force`.
2. Open the PR against the profile's base branch with this body:

```
## What and why
<two or three sentences; link the spec>

## Acceptance criteria
| AC | Result | Evidence |

## Checks
<command> → <result>; baseline failures: <names>

## Risk
- Blast radius: <what could break, for whom>
- Migrations / data changes: <none, or what runs and whether it's safe while serving>
- Reversible: <two-way door (revert the PR) / one-way door (why, and what undoing needs)>
- Rollback: <steps>

## Decisions
<ADRs added or followed>
```

3. Follow your harness's instructions for after a PR is opened, such as binding it so CI is watched. Report the PR link.

## 6. Report

What was committed (hash, branch), what was pushed and where, the PR link, the checks result, and anything you left unstaged and why.
