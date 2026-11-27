# Project profiles

The global skills in `~/agent-workflow/skills/` work in any project. What differs per project lives in a **project profile**, so the skills stay generic and each project keeps its own knowledge. That covers how to run it, URLs, roles, languages, test commands, the design system, known debt and what must never be touched.

This README lives in `~/agent-workflow/profiles/` and is linked to `~/.claude/project-profiles/README.md`. The profiles themselves stay in `~/.claude/project-profiles/<repo>/`.

## Where a skill looks, first match wins
1. `<repo root>/.claude/project-profile.md`: a profile checked into the repo, shared with the team.
2. `~/.claude/project-profiles/<repo>/profile.md`: a personal profile.

`<repo>` is the repository name from the `origin` remote, so every clone and worktree of a repo finds the same profile:

```bash
REPO=$(basename -s .git "$(git remote get-url origin 2>/dev/null)" 2>/dev/null)
[ -n "$REPO" ] || REPO=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
echo "$REPO"
```

A profile folder can also hold:
- `workflow.json`: the checks `run-checks` runs and the commands `guard-commands` blocks in this project (format below). The same lookup applies, so `<repo root>/.claude/workflow.json` wins.
- `design-system.md`: the design intent and decisions for `check-design`.
- `design-scan.json`: settings for `check-design`'s drift scan (see `~/.claude/skills/check-design/scripts/scan_design.py --help`).

## `workflow.json`

```json
{
  "checks": [
    {"name": "backend tests", "cwd": "backend", "run": ".venv/bin/python manage.py test app.tests"},
    {"name": "frontend typecheck", "cwd": "frontend", "run": "npx tsc -p tsconfig.app.json --noEmit", "timeout_minutes": 5}
  ],
  "blocked_commands": [
    {"pattern": "\\bmysqldump\\b", "reason": "A live mysqldump locks every table and takes the API down."}
  ]
}
```

- `checks`: the full suite, run in order from the repo root (`cwd` is relative to it). `run-checks` runs all of them; agents run it only for features built with `build-feature` (`AGENTS.md` §4). A check that runs longer than its `timeout_minutes` (default 20) is killed and counts as failed.
- `blocked_commands`: Python regular expressions matched against every shell command an agent runs in this repo, with the reason shown when one is blocked.

## No profile yet
The skill works out what it needs from the code and the running app (step 0 of each skill). At the end it offers to save what it learned as a profile, so the next run starts faster. Use the template below. Leave out sections that don't apply, and don't guess: only write down what you verified.

## Template

```markdown
# <Project name>

## Stack and layout
- <e.g. Django backend in `backend/app/`, React + TypeScript (Vite) frontend in `frontend/src/`>
- Base branch for "the branch" diffs: `<main>` (check: is it where recent merges land?)
- Routes are defined in: `<file>`

## Running it
- Frontend: `<url>`; backend/API: `<url>`
- Who starts the dev servers: <the user, in their own terminals / `<command>`>
- Signing in: <which accounts or roles to use; test credentials only if the project has them>

## Data safety (preflight)
- <How to check that the app talks to local or dev data, never production. Exact commands.>
- <Hosts, databases or services that must never be touched.>

## Users and permissions
- Roles: <list, and what each can do>
- Other states that change what a user sees: <trial ended, deleted users, feature flags…>

## Languages
- Locales: <en, nl…> in `<path>`; check script: `<command>`
- The language most customers use: <…>; strings there run <n>% longer.
- Locale formats to test: <e.g. Dutch decimal comma `1,5`, dates>

## External side effects
- <Email, messages, payments, webhooks, invoices… that a tester must stop short of>

## Checks
- Full suite: `~/agent-workflow/bin/run-checks` (configured in `workflow.json`)
- Single module: `<command>`
- Type checker: <command, or "none">
- Known failures on <base branch> (<date>): <test names>. Treat them as baseline, not as new failures.

## Conventions
- <Where helpers live, how API calls are made, state/data fetching library, error handling style, test style>

## Personas (feature-qa)
- <Optional: three personas that fit this product's users>

## Reports
- Write reports to: `<dir>` (default `~/.claude/reports/<repo>/<skill>/`)

## Known debt
Design flaws the user chose not to fix yet. Agents don't report these again unless a task makes them worse or depends on them.
| Where | Flaw | Date | Why not now |
|---|---|---|---|
```
