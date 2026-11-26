---
name: design-feature
description: Design how to build a scoped feature before writing code. Takes an approved spec (from scope-feature) and produces the design: data model and migrations, transaction boundaries and race guards (ACID), components and responsibilities (SOLID, high cohesion, low coupling), what existing code to reuse (DRY), the simplest shape that meets every acceptance criterion (KISS, YAGNI), test seams and thin vertical slices. For non-trivial designs it compares two or three genuinely different designs before picking one, challenges its own weakest points, and records hard-to-reverse decisions as ADRs. The user approves the design before build-feature starts. Use this after a spec is approved, or when the user asks to "design", "architect", "plan the implementation of" or "how should we build" something. Not for scoping requirements (use scope-feature first) or for small changes that scope-feature already designed inline.
---

# Design feature

Decide **how** to build what the spec says, before any code is written, so the implementation is small, consistent with the codebase and correct under concurrency and failure. The design is the simplest one that meets every acceptance criterion; anything it adds beyond that has to justify itself against a criterion.

The output is the spec's **Design, Test plan and Slices sections**, filled in, plus any ADRs. `build-feature` starts only after the user approves them.

Paths below starting with `~` are in the user's home folder.

## 0. Inputs

- **The approved spec** from `scope-feature` (the profile's report folder, or `~/.claude/reports/<repo>/scope-feature/`). No spec, or one the user hasn't approved: run `scope-feature` first.
- The project profile, the repo's `AGENTS.md`/`CLAUDE.md`, and the ADRs in `docs/adr/` that touch this area. An accepted ADR is a constraint; a design that contradicts it needs a new ADR that supersedes it, agreed with the user.
- The code the feature touches, read in full. Scoping already read some of it; re-read what the design depends on rather than trusting memory.

## 1. Find what to reuse and what to respect

Before inventing anything, list with file paths:
- **Existing helpers, services, components and patterns** the feature should use (search the repo for the operations it needs; the profile's Conventions section names the usual places).
- **The existing pattern for this kind of thing** (how similar endpoints, jobs, forms or models are built). Follow it if it meets the principles in the global `AGENTS.md` §2. If it doesn't, note the flaw: you'll propose a better pattern in step 3 rather than copying it.
- **Known debt** from the profile that this design depends on or would make worse.

## 2. Sketch the candidates

For a small or obvious design, sketch one and go to step 3.

For anything with a real choice (a new data model, a new async flow, a new integration, more than one plausible place for the logic), **design it twice**: produce two or three genuinely different designs. In Claude Code, spawn one fresh-context sub-agent (`model: sonnet`) per design in parallel. Give each the spec path, the reuse list from step 1 and one constraint:
- "Smallest change: the fewest new concepts, tables and files."
- "Best fit for the existing codebase patterns."
- "Strongest guarantees: invariants in the database, no possible race, idempotent side effects."

Each returns a half-page sketch: data model, the transaction and guard per user action, the components and what each owns, the main interface signatures, and its own weakest point. Without sub-agents, write the sketches yourself one after another, each from a clean start.

Compare them against the acceptance criteria and `references/design-checklist.md`, and pick one, or graft the best parts together. The default winner is the simplest design that meets every criterion; a more complex one must name the criterion the simple one fails.

## 3. Write the design

Fill in the spec's Design section (template: the scope-feature skill's `references/spec-template.md`):

- **Data model and migrations:** tables and fields with types, nullability and defaults; the invariants the database enforces; the migration and backfill plan, and whether it is safe to run while production serves traffic.
- **Transactions and concurrency (ACID):** one row per user action: its transaction boundary, the invariants it protects, each race and its guard, and the side effects that run after commit and how they stay idempotent.
- **Components and responsibilities:** each new or changed module and the one thing it owns. Business rules in one place, pure where possible; I/O at the edges.
- **API and UI contract:** endpoints with request and response shapes, status codes and error bodies; UI states with their exact copy or i18n keys.
- **Failure modes and recovery**, and **security and permissions**.
- **LLM features:** the tier and why, then that tier's component checklist from `agent-harness`: the `must` components, the `should` ones you include, and the ones you skip with a reason. The tier choice gets an ADR.
- **Alternatives considered:** the candidates you didn't pick and why.
- **A better pattern, if step 1 found a flawed one:** the proposal, why it's better, and what happens to the existing usages (migrate now, migrate later as a tracked task, or leave them with a note). Agree this with the user before it goes into the design.

Then run `references/design-checklist.md` over the design.

## 4. Challenge it

Before showing it, name the design's **two weakest points**: the race you're least sure about, the migration that worries you most, the coupling you couldn't avoid. Fix them, or write in "Known risks and weak points" why they are acceptable.

Then delete what isn't needed: every table, field, option, flag, layer, abstraction and configuration value that no acceptance criterion requires.

## 5. Test seams and slices

- **Test seams:** propose the public interfaces the tests will go through, and confirm them with the user before any test is written. Prefer existing seams, and as few as possible: one high seam (an endpoint, a service function) is better than many internal ones. Tests at the seam survive refactors of what's behind it.
- **Test plan:** map every acceptance criterion to the test that proves it (file, test name, level).
- **Slices:** split the build into thin vertical slices. Each one goes through every layer it needs, ends in a working state, covers named acceptance criteria and fits in one focused session. If a preparatory refactor makes the change easy, make it the first slice, behavior-preserving and on its own. Avoid horizontal slices ("all models, then all views"): nothing works until the last one lands.

## 6. Decisions and approval

- Write an ADR with the `adr` skill for each decision that is hard to reverse, surprising without context, or a real trade-off, including the ADR candidates `scope-feature` noted and decisions the user made. Link them from the spec's ADRs section.
- Present the design in chat: the chosen shape in a few lines, why it beat the alternatives, the two weak points and how they're handled, the slices, and the ADRs. In plan mode, present it with `ExitPlanMode`.
- Get explicit approval. If the user changes something, update the spec file and the ADRs first.
- Then continue with `build-feature`.
