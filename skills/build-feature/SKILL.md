---
name: build-feature
description: Implement an approved spec and design, test-first, one thin vertical slice at a time. For each slice it writes the failing test for an acceptance criterion, watches it fail for the right reason, writes the least typed code that passes, refactors while green and runs the checks. It never weakens a test to get green, stops and raises it when the spec turns out wrong, collects flaws in adjacent code for the user instead of fixing them on the spot, and ends with an independent review and a per-criterion pass/fail report with evidence. Use this when the user approves a design, says "build it", "implement it", "go ahead", "start coding", or asks to implement a spec or a slice. Not without an approved spec (run scope-feature first), and not for bug fixes (use fix-bug).
---

# Build feature

Turn the approved spec into working code with tests, without scope creep, test weakening or silent deviations. Follow the global rules in `AGENTS.md`, especially §2 (principles), §4 (tests), §5 (types), §7 (scope) and §8 (adjacent code).

## 0. Preconditions

- An **approved spec with a design** (the profile's report folder, or `~/.claude/reports/<repo>/scope-feature/`): acceptance criteria, test seams, test plan and slices. If any of these is missing or not approved, stop and run `scope-feature` / `design-feature` first. Say so in one line.
- **Know the checks:** `~/agent-workflow/bin/run-checks --list` shows the project's full suite; the profile lists single-module test commands and **known baseline failures**. Run the full suite once before you start if no recent result exists, so you know the baseline and won't blame (or miss) failures later.
- **Shared checkout:** another session may be editing the same working tree. Never stash, reset, restore or switch branches; touch only the files your slice needs.

Copy the slices from the spec into your task list, one item each, plus "review" and "report" at the end.

**LLM features:** implement `agent-harness`'s standards first (stop reason, scoping in code, gated idempotent writes, logging every step, bounds). Unit tests with a fake model client prove the plumbing; the eval set from the spec proves the answers. Rerun the evals whenever the prompt, model or tools change. They cost real model calls, so they're not part of `run-checks`.

## 1. For each slice: red, green, refactor

1. **Red.** Write the test for the slice's next acceptance criterion at the agreed seam, named after the behavior (`test_second_approval_does_not_create_a_second_invoice`). Expected values are literals from the spec. Test through the public entry point a caller would use, with the spec's own examples and every input form it allows (a "number" means a whole number and a decimal). Run it and **watch it fail for the right reason**: an assertion about the missing behavior, not an import error, a typo or a broken fixture. A test that passes before the code exists proves nothing; fix the test.
2. **Green.** Write the least code that makes it pass, following the design: the components, transaction boundaries, race guards and reuse it names. Type everything (`AGENTS.md` §5). Don't add what no criterion asks for.
3. **Repeat** red and green for the slice's other criteria, one test at a time. Don't write all the tests first.
4. **Refactor** while everything is green: remove duplication you introduced, improve names, simplify. Behavior stays the same, and tests stay unchanged.
5. **Check** the slice: run the tests of the modules you touched, then the type checker and linter on the changed files if the project has them. Then tick the slice off.

When a test you didn't write starts failing, the code is wrong until proven otherwise. Find out why. Change that test only if the spec deliberately changed the behavior it checks, and name that decision in your report. Never delete, skip or loosen a test, change an expected value or widen a tolerance to get green. If the `flag-test-edits` hook warns you, take it seriously.

## 2. When reality disagrees with the spec

If the code shows the spec or design is wrong or incomplete (an invariant the design missed, an API that doesn't exist, a criterion that conflicts with another), **stop and raise it** with the user: what you found, the evidence (`file:line`), and your recommended change. Don't improvise around it. After agreement, update the spec (and the ADR if it's a decision), then continue.

Check every API, function, parameter and flag you use against its source or docs before relying on it (`AGENTS.md` §7).

## 3. Adjacent code

While building, note design flaws in code you didn't write that the feature touches or depends on (`AGENTS.md` §8), with `file:line`, but don't fix them. Check the profile's Known debt list first. They go into the final report with the required six points.

## 4. Finish

1. **Full checks:** run `~/agent-workflow/bin/run-checks`. Compare failures with the profile's known baseline; any other failure is yours to fix.
2. **Clean up:** remove debug output, commented-out code, unused imports, parameters and helpers you added, and anything no criterion needed. Run the checks again if you changed code.
3. **Review:** run `review-change` on this conversation's changes. Fix the must-fix findings that are in your own change and rerun the checks. Report the rest.
4. **Verify the criteria:** fill in the spec's Verification table, one row per acceptance criterion: pass / fail / not verified, with the evidence (the test name and its result, the query output, the UI check). In Claude Code, the `verifier` sub-agent can do this independently; it is required when the criteria include manual checks. Never mark a criterion as passing without having run its check.
5. **Report** in chat, following `AGENTS.md` §11: what was built, the criteria table, the checks command and result (including baseline failures), the failure-pattern self-check, adjacent-code findings with the six points, any rule proposals, and what's not done or not verified.
6. Suggest the next steps that fit: `feature-qa` to try it in the running app, `check-design` for UI work, `ship` when the user wants to commit. Don't commit or push unless the user asks.
