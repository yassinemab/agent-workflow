---
name: retro
description: Look back at a finished feature, fix or session and turn what went wrong into lasting improvements to the agent workflow. It finds failure patterns that occurred, user corrections, checks that caught a mistake, skipped or wrong skill steps, and rules that were unclear or bloated. For each it proposes the strongest fix, with an enforced check (type, lint, test, hook) preferred over more rule text, and shows the exact change. It applies only what the user approves, as commits in ~/agent-workflow. Use this when the user says "retro", "what did we learn", "what went wrong", "improve the workflow", "update the rules", or after a feature ships. The quick version of this runs at the end of every turn (AGENTS.md §11); this skill is the deeper pass.
---

# Retro

Make the next session better than this one by changing the environment, not by hoping the agent remembers. Each lesson becomes the strongest enforcement that fits. A lesson that stays only in chat is lost.

**Nothing in `~/agent-workflow` changes without the user's explicit yes** to that specific change (`AGENTS.md` §11). The `guard-rule-files` hook asks before writes to the global rules; that is a backstop, not the permission.

## 1. Collect evidence

From this conversation, the diff, the review reports, the check results and the spec, list what actually happened. Each item needs a concrete reference: a message, a `file:line`, a command and its output.
- **Failure patterns hit** (`AGENTS.md` §10): duplication, over-engineering, inconsistency, a silent behavior change, a weakened test, an invented API, a security hole, a big rewrite, missing error handling, or claiming "done" without evidence.
- **User corrections:** every time the user said "no", "that's wrong", "I said…", or redid something.
- **Caught by a check:** hook decisions in `~/.cache/agent-workflow/events.jsonl` (denials, blocks, warnings and crashes, across all sessions), hook blocks, `flag-test-edits` warnings, failing checks, review must-fix findings. These show the safety net working; ask whether the mistake could have been prevented earlier.
- **Skill problems:** steps that were skipped, steps that didn't fit the situation, missing steps, unclear wording, skills that triggered when they shouldn't or didn't when they should.
- **Friction:** repeated manual work, slow or noisy checks, missing project facts that had to be rediscovered (they belong in the profile).

If nothing went wrong, say so and stop. A retro with no findings is a good outcome.

## 2. Pick the strongest fix for each

Use the first rung that fits:
1. **Make it impossible:** a type, a database constraint, or an API shape that can't be misused. This is a change to the project, so propose it as a task.
2. **Make it fail loudly:** a lint rule or a test whose error message names the fix. Also a project change.
3. **A hook or a check** in `~/agent-workflow`: for example, a new `guard-commands` rule, or a `blocked_commands` entry in the project's `workflow.json`. Prove it would have caught this real mistake: add a test in `~/agent-workflow/tests/` that feeds it the actual command or edit.
4. **A skill step** in `~/agent-workflow/skills/`: when the mistake came from a missing or unclear step in a procedure.
5. **A project fact** in the project profile: when the agent lacked knowledge about this repo.
6. **Rule text** in `~/agent-workflow/global/AGENTS.md`, last. Word it generically: the repo may be published, so a lesson from one project goes in that project's profile, and the global rule keeps only the general part. `run-checks` in `~/agent-workflow` scans for project names, hosts and personal data.

When the mistake was the wrong skill (or none) for a request, also propose an eval case in `~/agent-workflow/evals/cases.json` with the user's actual wording, so `run-evals` catches it next time. Read the existing rules first. If one already covers it, the problem is its wording or placement, so reword it rather than adding a near-duplicate. Keep the file under about 200 lines: when adding, look for something to merge or cut.

## 3. Propose

Present the proposals most severe first, one block each:
```
### <short title>
What happened: <the evidence>
Fix (rung N): <file> — <the exact change: the lines added or edited, or the test and hook rule>
Why this rung: <why a stronger one doesn't fit, if it isn't rung 1–3>
Cost: <what it adds: lines in AGENTS.md, check time, false positives>
```
Ask for a yes or no per proposal. Use the harness's question tool if it has one, otherwise a numbered list.

## 4. Apply only what was approved

- Make each approved change in `~/agent-workflow` (or the project, for rungs 1, 2 and 5).
- For hook and check changes, add the test first. Watch it fail, then make the change, then run the workflow's checks (`cd ~/agent-workflow && bin/run-checks`). Its suite is fast, so it counts as targeted (`AGENTS.md` §4), and it includes the secret scan this repo needs.
- Commit each approved change in `~/agent-workflow` with a message that names the incident it prevents. The user's yes to the change includes this local commit, but not a push.
- If a change touches the installed layout (a new skill, agent or hook), run `python3 ~/agent-workflow/install.py`.
- After a change to a skill or a rule, run `~/agent-workflow/bin/run-evals` and report the result. It runs headless Claude sessions on the user's subscription (a few minutes, roughly a long session's worth of usage), so say that before running it.
- Report what changed, with the commit hashes, and the declined proposals in one line each.
