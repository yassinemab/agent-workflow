---
name: refine-code
description: Review-and-improve loop for code quality in the current project, in any language or stack. A fresh reviewer checks the code for clarity, DRY, reuse of existing helpers, and software design principles (single responsibility, cohesion, coupling, naming, YAGNI). Claude then simplifies or improves it while proving no functionality is lost (behavior contract, characterization tests, a separate equivalence review), and a new reviewer checks again. This repeats until the code is good or stops improving. Use this whenever the user says "refine this", "clean up this code", "make this code better", "simplify and re-check", "is this code good", "DRY this up", "refactor until it's clean", "run the quality loop", or asks for a code-quality pass on a branch, file, feature or diff, even if they don't say "loop". With nothing named it refines what the current conversation changed, not the whole branch. Not for hunting functional bugs (use code-review) or UI/UX (use check-design).
---

# Refine code

A loop of **review → improve → prove nothing broke → review again** over a bounded piece of code, until a reviewer who has never seen it finds nothing worth changing.

**The one hard rule: no functionality is lost.** Every input that worked before gives the same output, the same side effects (DB writes, emails, API calls, events), the same errors and status codes, and the same UI behavior afterwards. Simpler code that does less is a regression, not a refinement. Code is only "dead" when you've proven nothing reaches it. When in doubt, keep the behavior and leave the code as it is.

Three safeguards make that hold, and none of them is optional:
1. **A behavior contract** written before any edit (step 2), so "the same behavior" means something concrete.
2. **Tests that pin current behavior** (step 2), run after every round (step 3d).
3. **A separate equivalence reviewer** each round (step 3d) whose only job is to find behavior changes in the diff. It isn't the quality reviewer, and it doesn't care whether the code got nicer.

The quality reviewer is also fresh each round: a reviewer that knows what you changed tends to approve it.

Paths below starting with `~` are in the user's home folder. Expand them to absolute paths when you pass them to a sub-agent or a file tool.

## 0. Learn the project
Find the project profile (how profiles work: `~/.claude/project-profiles/README.md`):
```bash
REPO=$(basename -s .git "$(git remote get-url origin 2>/dev/null)" 2>/dev/null)
[ -n "$REPO" ] || REPO=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
ls "$(git rev-parse --show-toplevel)/.claude/project-profile.md" ~/.claude/project-profiles/"$REPO"/profile.md 2>/dev/null
```
Read it (the repo's `.claude/project-profile.md` wins). You need its **stack and layout**, **checks** (test, typecheck and lint commands, known failures), **conventions** and **base branch**. Without a profile, work these out before step 1:
- **Stack and layout:** languages, frameworks, where each part lives (`README`, `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile`, `pom.xml`, …).
- **Checks:** how tests, the typechecker and the linter run, and roughly how long they take. Package scripts, a `Makefile` and the CI workflows (e.g. `.github/workflows/`) are the most reliable sources.
- **Conventions:** where shared helpers live, and how API calls, data fetching, errors and tests are written. Read two or three neighbouring files in the scope's area.
- **Base branch:** the one recent merges land on. Usually `origin/HEAD`, but check it isn't stale.

## 1. Scope

Decide what is in scope, and keep every edit inside it:
- Named files, folder or feature: those.
- **Nothing named: what this conversation changed, not the branch.** The branch and the working tree can hold unfinished work from other conversations.
  - List the files this conversation created or edited (your own Edit/Write calls, plus changes the user made and discussed here), and write the list down.
  - Read their current changes with `git diff -- <files>`, and new files in full.
  - Where a file also holds changes this conversation didn't make, refine only the parts this conversation changed.
  - If this conversation changed nothing, ask what to refine.
- "this branch": only when the user asks for it. Start from `git diff <base>...HEAD --stat` plus uncommitted changes (`git status`).
- Always ignore generated files, auto-generated migrations, lockfiles, build output, report folders, CSVs and data dumps.
- If the scope is above ~1,500 changed lines, say so and ask which part to start with. A loop over everything at once produces shallow reviews.

**This checkout can be shared with another session.** Before editing, run `git status` and note which uncommitted changes are not part of your scope. Never use `git stash`, `git checkout -- <file>`, `git restore` or whole-file rewrites to undo things; undo your own changes with targeted edits. Never commit unless the user asks.

**Snapshot the originals.** Copy every in-scope file to the scratchpad (`<scratchpad>/refine-baseline/<same relative path>`) before the first edit. This is a read-only reference for the final comparison (step 4), never something to copy back over the working tree.

## 2. Baseline: behavior contract and pinned behavior

### a. Behavior contract
Write down, per in-scope unit (endpoint, service function, component, hook, class), what it does today. Read the code *and its callers*:
- **Interface:** public names, signatures, URL routes, request/response fields and status codes, props, exported helpers, i18n keys, named routes, background job and task names, CLI commands, JSON keys other code reads.
- **Behavior:** outputs for normal inputs, and the edge cases the code handles (empty, null, zero, negative, invalid format, duplicates, permissions, wrong state).
- **Side effects and their order:** DB writes and transactions/locks, emails, external API calls, events/audit rows, cache, local storage, navigation, toasts.
- **Errors:** which exceptions, messages and status codes, and where they are caught.

Keep it short: a bullet list per unit. This is what the equivalence reviewer checks against.

### b. Pin behavior with tests
Use the project's checks from step 0.
- **Tests:** find the tests that cover the units (search the test folders for the module or function name) and run them. For any contract item that no test covers, and that a refactor will touch, **write a characterization test first**. It asserts what the code does now, including edge cases and side effects (mock email, HTTP and other external calls the way neighbouring tests do). It must pass on the unchanged code. Put it next to its neighbours, in their style, and keep it; it's part of the result.
- **Static checks:** the typechecker and the linter on the touched files.
- **No test runner for part of the scope** (common for frontends): don't add one unasked. Pin behavior instead with:
  - A **browser walkthrough** of each affected screen in the running app (if the dev servers run), done before the first edit and again at the end. Note what you did and what you saw: states, labels, validation messages, network calls.
  - For pure helpers (formatting, parsing), a table of inputs, including edge cases, run before the first edit and compared after the last. With a Vite dev server you can call the module from the browser console (`javascript_tool`: `const m = await import("/src/utils/amount.ts"); ["1.234,56", "", "-5"].map(m.normalizeAmount)`); otherwise use the language's REPL or a scratch script outside the repo. With the built-in browser pane this needs the pane visible: a hidden pane freezes the page's timers and promises. If it stalls, ask the user to show the pane, or check the same inputs through the UI. Don't install a test runner for this.
- Write the baseline down (pass/fail per check, including the profile's known failures). Pre-existing failures are not yours to fix, but you must not add new ones.

## 3. The loop

Run at most **4 rounds**. Each round:

### a. Quality review (fresh sub-agent)
Spawn one `general-purpose` sub-agent (`model: sonnet`) with the brief below, filled in. Give it the file list and the base to diff against, not your opinions or earlier findings.

> You are reviewing code quality in <project: one line on the stack and layout, e.g. "a Django backend in `backend/app/` and a React + TypeScript frontend in `frontend/src/`">. Review only these files and changes: <the scope from step 1: file list, plus `git diff -- <paths>`; for files that also hold other work, name the functions/lines in scope>. Read each file in full, plus the code it calls and the code that calls it, so you can judge reuse and fit.
>
> Judge the code against the rubric in `<absolute path>/refine-code/references/rubric.md` (read it first), and against this project's conventions: <a few lines from the profile or step 0: where helpers live, how API calls, data fetching, errors and tests are written>. Report only changes that make the code clearly better for the next person who reads or changes it; don't report personal taste, and don't propose abstractions for code that exists once. Every proposed change must keep behavior identical. If a cleanup would change behavior, report it as a bug or question instead. If the code is already good, say so; "no findings" is a valid and welcome answer.
>
> Return:
> 1. A score from 1 to 5 per rubric dimension, with one sentence each.
> 2. Findings, most important first. Each with: severity (**must** = will cause bugs or real maintenance pain, **should** = clear improvement, **nit** = minor), `file:line`, what's wrong, the concrete change (name the existing helper to reuse, the function to extract, the name to use), and why it keeps behavior identical.
> 3. Any functional bugs you noticed, separately. Don't mix them into the quality findings.
>
> Read only. Don't edit files.

### b. Decide
Go through the findings yourself. You own the result; the reviewer advises.
- Apply every **must** and every **should** you agree with *and* can do without changing behavior. Skip a finding when it contradicts the codebase's conventions, needs a behavior change, or makes the code longer without making it clearer; note why.
- **Nits:** apply only the cheap, obviously right ones.
- Functional bugs: don't fix them here, even if the fix looks trivial. Fixing a bug *is* a behavior change. Collect them for the report.

### c. Improve
Make the changes in small, separate edits, one theme at a time (e.g. "reuse the existing `formatCurrency()` helper", then "split `submit()` into parse and persist"). Match the surrounding style. Watch for these silent behavior changes, which are the usual way refactors lose functionality:
- **Deleting "dead" code.** Prove it's dead first: search for every reference, including string-based ones (URL paths, i18n keys, named routes, task names, JSON keys, reflection and dynamic imports, templates, config, tests). Nothing found → delete; anything found → keep.
- **Merging "duplicates"** that differ in a detail: a default, a rounding mode, an error message, a permission check, a filter on a query, the order of side effects.
- **Changing defaults, truthiness or types:** `or` vs `??`, `if x` vs `if x is not None` (0 and "" are valid values), integer vs float vs decimal, `==` vs `===`, sort stability, timezone handling.
- **Moving code across a transaction, lock, `try`/`catch`, `await`, thread or effect boundary.** This changes what is atomic, what is caught, or when something runs.
- **Renaming public things:** APIs, URLs, database fields, i18n keys, props used elsewhere, exported names. Don't, unless the finding is about exactly that and nothing outside the scope depends on it.
- **Swallowing or reshaping errors:** same exception types, messages, status codes and logging as before.

### d. Verify: prove behavior is unchanged
1. **Re-run the pinned checks** from step 2b: tests, typechecker, linter. A check that passed before must pass now. If one fails, find the edit that caused it and undo that edit (targeted edit, not git restore). Never "fix" the test to match the new code; the test describes behavior that must not change.
2. **Equivalence review (fresh sub-agent, every round).** Spawn a separate `general-purpose` sub-agent (`model: sonnet`) with:
   > You are checking a refactor for behavior changes. Nothing else matters: not style, not quality. Here is the behavior contract: <contract from step 2a>. Here is this round's diff: <`git diff -- <in-scope paths>` for this round's edits, or a diff against the previous round's copies>. Read the full files around each hunk. For every hunk, decide whether any input, state or timing could now produce a different result, side effect, error, status code, rendered UI, network call or navigation than before. Pay special attention to deleted code (is it really unreachable?), merged code paths, changed conditions and defaults, error handling, transaction/lock/await boundaries, and anything public or string-referenced. Return a list: `file:line`, the behavior that changed, an input that shows it, and a confidence. If you find none, say "no behavior change found" and list what you checked. Read only.

   Every confirmed behavior change gets undone before the round ends. If it's a real improvement in disguise (it fixes a bug), undo it anyway and list it under "Bugs noticed".
3. Never leave a round with a failing pinned check or an unresolved equivalence finding.

### e. Stop or go again
Stop when any of these is true:
- The fresh quality reviewer returns no **must** or **should** findings. That is the goal.
- Every dimension scores 4 or higher and only nits remain.
- The reviewer starts asking to undo something an earlier round changed, or the same finding comes back after you fixed it. The loop is oscillating; stop and mention it.
- Round 4 is done.

Otherwise start the next round with a new quality reviewer on the updated code.

## 4. Final behavior check

Before reporting:
- Run every pinned check one last time.
- Run one more equivalence review over the **whole** change: the original files in `<scratchpad>/refine-baseline/` against the current files, with the contract. A sequence of individually safe rounds can still add up to a change, so this pass looks at the total.
- Redo the browser walkthrough from step 2b, if you did one, and compare it with what you noted before the first edit.
- If anything differs and you can't make it identical, undo the edits involved and say so in the report.

## 5. Report

End with a short report in chat:

```markdown
## Refine: <scope>, <N> rounds

**Result:** <Good / Better, with open points / Stopped: oscillating or out of rounds>
**Scores:** round 1 → final, per dimension (e.g. DRY 2 → 4)

### Behavior preserved
- Pinned checks: <check>: baseline → final (e.g. invoicing tests 32/32 → 32/32 + 6 new characterization tests; typecheck clean → clean)
- Equivalence reviews: <N rounds + final>, <findings and what was undone>
- Browser walkthrough: <screens checked, same result before and after>

### What changed
- <theme>: <files>, <one line on why it's better>

### Skipped findings
- <finding>: <why it was skipped (e.g. would change behavior)>

### Bugs noticed (not fixed)
- <file:line>: <what>, <how it would show up>
```

Then show the diff summary (`git diff --stat -- <scope>`). Leave committing to the user.

**No profile yet?** Offer to save what you worked out in step 0 as `~/.claude/project-profiles/<repo>/profile.md` (template in the README there), so the next run skips that step. Write only what you verified.
