# <Feature name>: spec

Status: <draft / approved YYYY-MM-DD>
Repo / branch: <repo> / <branch>

## Goal
<Who does what, and why. Two or three sentences. The problem it solves.>

## Scope
**In scope:**
- <…>

**Out of scope (explicitly, with reason):**
- <… : v2 / not needed for the goal / handled by X>

## Context
- Existing code this builds on or must stay consistent with: <`path/file.py:line` and what it does>
- Reused helpers, components and patterns: <paths>
- Relevant invariants already in place: <constraints, state machines, permission checks>

## Decision log
| # | Question | Decision | Reason | Decided by |
|---|----------|----------|--------|------------|
| D1 | <…> | <…> | <…> | user / Claude ("your call") |

## Acceptance criteria
| ID | Given | When | Then (observable) | Checked by |
|----|-------|------|-------------------|------------|
| AC1 | <state> | <action> | <response / rows / events / UI text> | <test file::test name / query / curl / UI steps> |
| AC2 | … | … | **Must not:** <…> | … |

## Design
_Filled in by `design-feature` (or a five-line design for a small change)._

### Data model and migrations
- <Tables and fields, types, nullability, defaults>
- DB-enforced invariants: <unique / FK on_delete / check / NOT NULL>
- Migration and backfill plan; safe to run while prod is serving: <yes, because… / two-step deploy: …>

### Transactions and concurrency (ACID)
| User action | Transaction boundary | Invariants | Race and its guard | Side effects (after commit, idempotent how) |
|-------------|----------------------|------------|--------------------|---------------------------------------------|
| <…> | <…> | <…> | <…> | <…> |

### Components and responsibilities
- <module/service/component>: <the one thing it owns>

### API and UI contract
- <METHOD /path>: request <…>, response <…>, errors <status + body>
- UI states: loading / empty / error / partial / denied: <exact copy or i18n keys>

### Failure modes and recovery
- <External call X fails/times out → behavior, what the user sees, how it's retried or repaired>

### Security and permissions
- <Who can do what; how workspace scoping is enforced; input validation>

### Alternatives considered
- <Option>: rejected because <…>

### ADRs
- <docs/adr/NNNN-slug.md: the decision it records>

### Known risks and weak points
- <Risk>: <mitigation or why it's acceptable>

## Test plan
Test seams (the public interfaces the tests go through, agreed with the user): <…>

| AC | Test / check | Level (unit / integration / e2e / manual) |
|----|--------------|-------------------------------------------|

## Slices
Each slice is a thin, working, demoable piece through every layer it needs, built test-first.
1. <Slice>: covers <AC ids>; done when <tests named above pass and run-checks ran>
2. …

## Verification (filled in after implementation)
| AC | Result (pass / fail / not verified) | Evidence |
|----|-------------------------------------|----------|
