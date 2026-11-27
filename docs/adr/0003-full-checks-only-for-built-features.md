# 0003. Full checks only for built features, and no hook that enforces checks

- Status: Accepted
- Date: 2026-11-27
- Decided by: user (all three points below)

## Context
A Stop hook (`require-checks`, fed by `track-turn` and `track-edits`) kept a turn from ending until `run-checks` had covered every file the session edited, and the rules required the full suite after every code change. In practice the full suite ran far too often: on a one-line edit, on each small fix, at every review round. For small changes that cost was out of proportion to what it caught.

## Decision
- The full suite (`run-checks`) runs only for a feature that went through the whole lifecycle: `scope-feature`, `design-feature`, `build-feature`.
- Everything else (quick and small changes, bug fixes, refactors, review fixes) runs targeted tests: the tests of the touched modules and of the modules that call what changed (`AGENTS.md` §4). `ship` follows the same rule.
- The `require-checks`, `track-turn` and `track-edits` hooks are removed, along with the code that only fed them: per-turn edit state, the result `run-checks` saved after each run, and the `no_checks_needed_for` setting. `workflow.json` still accepts that key and ignores it.

## Alternatives considered
- Keep the hook, but only in sessions that loaded `build-feature`: it keeps enforcement where the full suite is required. Rejected by the user in favor of the simpler setup.
- No tests at all outside the feature flow: rejected, because a small change can still break things.
- `ship` always runs the full suite: rejected, so that small changes don't pay the full cost at commit time either.

## Consequences
- Small changes finish faster, and agents no longer get blocked at the end of a turn.
- "Claiming done without evidence" (`AGENTS.md` §10) is now guarded only by rule text, which goes against the preference for enforced checks in §11.4. A cross-module regression that the targeted tests miss can now reach a commit.
- Revisit this if such regressions show up. The lighter alternative above is the first thing to try.
