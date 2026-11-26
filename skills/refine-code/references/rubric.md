# Code quality rubric

The principles (§2) and known AI failure patterns (§10) in `~/agent-workflow/global/AGENTS.md` are the standard. This rubric turns them into review checks with scores. When the two disagree, AGENTS.md wins.

Score each dimension 1–5 (1 = actively harmful, 3 = acceptable, 5 = exemplary). A finding must point at a line and say what to do instead. Over-engineering counts as a finding as much as duplication does.

## 1. Clarity
- Names say what a thing is or does in the domain's words (`invoice`, `sender_account`), not how it's built (`data2`, `handleStuff`, `tmp`).
- A function can be understood without scrolling; one level of abstraction per function (no mix of HTTP parsing, business rules and formatting in one body).
- Control flow is flat: early returns over deep nesting; no boolean flags that switch a function between two jobs.
- Comments explain *why*, never restate *what*. Stale or misleading comments are findings.
- Magic numbers and strings have a named constant when they mean something (`REMINDER_DAYS`), not when they're obvious (`0`, `1`).

## 2. DRY and reuse
- The same logic in two or more places (including frontend and backend computing the same thing differently) → one source of truth.
- **Reuse before you write:** search the repo for an existing helper before accepting a new one (`grep -rn` for the operation). Typical places: utility and service folders, shared component folders, and helper modules next to the feature (the project profile names them when it has them).
- Copy-pasted markup or style/class strings repeated across components → a component, or an existing design-system class or component.
- DRY is about knowledge, not text: two lines that look alike but change for different reasons should stay separate. Don't merge them.

## 3. Design principles (applied pragmatically)
- **Single responsibility:** a module/class/function has one reason to change. Request handlers parse and authorize; services hold business rules; serializers or presenters shape output.
- **Cohesion and coupling:** things that change together live together; a module doesn't reach into another's internals (private attributes, raw querysets of another app's models where a function exists).
- **Explicit dependencies:** pass what a function needs; avoid hidden global state, module-level mutable caches without invalidation, reading env vars deep inside logic (read them in one config place).
- **YAGNI:** no parameters, hooks, base classes or config options with one caller "for later". Remove dead code, unused exports and unreachable branches.
- **Consistent error handling:** errors are raised/returned in the codebase's existing style; no swallowed exceptions (`except Exception: pass`), no errors turned into success responses.
- **Data integrity:** multi-step writes in a transaction; checks and writes under the same lock when concurrency matters.

## 4. Simplicity
- The simplest code that does the job: fewer branches, fewer intermediate variables, standard library and framework features over hand-rolled ones (database aggregations over loops in application code; the project's data-fetching library over hand-managed fetch state where the codebase already uses it).
- No premature generality: one concrete function beats a configurable framework with one use.
- Long parameter lists, long UI components (>~300 lines) or files mixing unrelated concerns are split along real seams.

## 5. Fit with the codebase
- Follows the conventions already in the surrounding code and the project profile (file layout, naming, how text is translated, how API calls are made, how handlers and services are structured).
- Types: no `any` where a type exists; backend and frontend types for the same payload agree.
- Tests: new behavior has tests next to their neighbours, in their style; refactors keep tests green without loosening them.

## Severity guide
- **must:** will likely cause bugs, data problems or significant maintenance pain (duplicated money logic that can drift, swallowed errors, a 400-line component no one can change safely).
- **should:** a clear improvement a good reviewer would ask for in a PR.
- **nit:** small polish; optional.
