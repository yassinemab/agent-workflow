# 0001. Run the "without workflow" arm of the quality evals with CLI flags

- Status: Accepted
- Date: 2026-11-27
- Decided by: user and agent, while designing the quality evals

## Context
The quality evals compare the same tasks with and without the workflow. The "without" arm must load none of the skills, global rules, subagents or hooks, but still run on the user's Claude subscription. `--bare` skips all of that, but it needs an API key and can't use the subscription login.

## Decision
The "without" arm runs `claude -p` with `--setting-sources project --disable-slash-commands`. On 2026-11-26 this was checked to load no skills and no custom subagents, to load no global rules (asked about them, a session answered no where the normal setup answered yes), and to run no hooks (no turn state was written). The evals are a tier 2 workflow: code runs fixed steps, and the model appears only in the sessions being tested and in the judge.

## Alternatives considered
- `--bare`: needs an API key, so it can't use the subscription.
- A temporary home folder: loses the subscription login, and it's harder to be sure what still loads.

## Consequences
- The arms differ only in these two flags, so a difference in results comes from the workflow.
- If a future Claude Code version changes what these flags skip, the "without" arm quietly becomes contaminated. Rerun the check (does the session see the rules or skills?) after Claude Code updates.
