---
name: adr
description: Record an architectural decision as an ADR in the repository's docs/adr/ folder, including decisions the user made. Writes it only when the decision is hard to reverse, surprising without context, or a real trade-off, and handles numbering, superseding an older ADR, and linking it from the spec. Use this when a design or conversation settles something like a new pattern, a new dependency, a data model shape, a deliberate deviation from an existing pattern, or a hidden constraint; when the user says "write an ADR", "record this decision", "document why we chose X"; or when another skill (design-feature, refine-code, fix-bug) calls for one. Not for routine implementation choices.
---

# ADR

An ADR tells a future developer or agent **why** the code is the way it is, so they don't undo a deliberate decision or repeat a rejected alternative. Too many ADRs bury the important ones, so write one only when it earns its place.

## 1. Does it need an ADR?

Write one when at least one of these is true:
- **Hard to reverse:** a data model, a public API shape, a dependency, a migration strategy, a vendor.
- **Surprising without context:** a future reader would likely "fix" it. Examples: a deliberate deviation from the codebase's usual pattern, a constraint from outside the code (a rate limit, a legal rule, a production incident).
- **A real trade-off:** there was a reasonable alternative, and choosing this one costs something.

Not for: naming, which file a helper lives in, choices any competent developer would make the same way, or things the code makes obvious. If in doubt, mention the decision in the spec's decision log instead.

## 2. Write it

1. Find the folder: `<repo root>/docs/adr/`. If it doesn't exist, create it. This is the global convention from `AGENTS.md` §6.
2. Read the existing ADRs' titles. If this decision changes an accepted one, the new ADR supersedes it: set the old one's status to "Superseded by NNNN", and say what changed in the new one's Context. Never edit an old ADR's decision in place.
3. Number it: the next free four-digit number (`0001`, `0002`, …). Name it `NNNN-short-slug.md`.
4. Fill in `references/adr-template.md`:
   - The title states the decision.
   - Context explains what made it non-obvious.
   - Alternatives are the real ones that were considered, not straw men.
   - Consequences include the cost.
   - Keep it short: a few paragraphs, often less.
   - Credit who decided. "Decided by: user" is important: it tells a future agent not to change it without asking.
5. Link it: add the ADR path to the spec's ADRs section if there's a spec, and mention it in the commit message when it ships.

## 3. Tell the user

Say in one line which ADR you wrote and what it records. ADR files are documentation, so they need no checks. They are still part of the change and get committed with it when the user ships.
