---
name: review-change
description: Independent review of a code change on two separate axes, by fresh reviewers who didn't write it. The standards axis checks the change against the global design principles (DRY, SOLID, ACID, KISS, cohesion and coupling), the known AI failure patterns, typing, and test integrity (deleted, skipped or loosened tests). The spec axis checks it against the spec's acceptance criteria: missing behavior, wrongly implemented behavior, and scope creep. Claude then verifies every finding against the code before reporting, and drops what doesn't hold. Use this when a feature or fix is done, before shipping, or whenever the user asks to "review", "check my change", "is this good", "review the diff", "review before I commit" or "review the branch". Always use this for a review request instead of reviewing the change yourself. With nothing named it reviews what this conversation changed, not the whole branch. Not for hunting functional bugs line by line (the built-in /code-review does that) or for refactoring (use refine-code).
---

# Review change

Two reviewers, two questions, kept apart:
1. **Standards:** is this change well built, by the rules in the global `AGENTS.md`?
2. **Spec:** does it do what the spec says: all of it, correctly, and nothing more?

Both run in fresh contexts. They haven't seen how the code was written, so they judge the result, not the intention. A reviewer that knows the reasoning tends to approve it. The review reports findings; it doesn't edit code.

## 1. Fix the scope

- **What changed.** With nothing named, review this conversation's changes. List the files you created or edited and get their diff (`git diff -- <files>`, plus the full content of new files). Another session may share the checkout, so leave out changes this conversation didn't make. "The branch" means `git diff <base>...HEAD`, with the base branch from the project profile.
- **Check the diff is what you think it is.** It's non-empty, it contains the change, and it contains nothing unrelated. Do this before spawning anyone.
- **The spec:** the spec file from `scope-feature`, if there is one. Without a spec, the spec axis reviews against the user's request as stated in the conversation, and says that it did.
- **Context:** the project profile (conventions, known debt, baseline failures) and the ADRs in `docs/adr/` that touch the changed area.

## 2. Run both reviewers in parallel

In Claude Code, spawn the `standards-reviewer` and `spec-reviewer` sub-agents at the same time, each with a fresh context. Give each:
- the list of changed files and the diff (or the command to produce it),
- the repo root and the profile path,
- the relevant ADR paths,
- and for the spec reviewer, the spec path.

Don't give them your own view of the change or your reasoning. That is what keeps them independent.

When the diff touches LLM or agent code (model calls, prompts, tool definitions, agent loops), also spawn a third reviewer (`general-purpose`, `model: sonnet`) that runs `agent-harness` in audit mode on the changed feature. Report its findings as a separate "Harness" section.

Without sub-agents (for example in Codex), run the two reviews yourself one after another. Start each from only the diff and its brief (`~/agent-workflow/agents/standards-reviewer.md`, `~/agent-workflow/agents/spec-reviewer.md`), not from memory of writing the code.

## 3. Verify every finding

Reviewer findings are claims, not facts. For each one:
- Open the code at the cited line and confirm the problem exists and is in the reviewed change. For an adjacent-code finding, confirm it's in code the change touches or depends on.
- Drop findings that are wrong, already handled elsewhere, contradicted by an ADR, listed as known debt in the profile, or matters of taste. Keep a one-line note of each dropped finding and why it was dropped.
- Keep the severity honest:
  - **must-fix:** a bug, data-integrity problem, security hole, weakened test, missing criterion, or a principle violation that will cause real pain.
  - **should-fix:** a clear improvement a good senior reviewer would ask for.
  - **nit:** optional polish.

## 4. Report

Report the axes separately. Don't merge or re-rank them.

```
## Standards
| Sev | Where | Finding | Principle / failure pattern | Suggested fix |
## Spec
| AC | Status (met / missing / wrong / not verifiable) | Evidence |
Scope creep: <code no criterion asks for, with file:line, or "none">
## Adjacent code (AGENTS.md §8)
<each with the six points>
## Dropped findings
<one line each>
```

Then:
- **The change is this conversation's own work:** fix the must-fix findings now, run the checks `AGENTS.md` §4 asks for (full for a feature built with `build-feature`, targeted otherwise), and run the review again on the fixed diff with fresh reviewers. Stop when no must-fix findings remain, or after three rounds, and report what's left. Ask the user about should-fix findings and nits.
- **Someone else's change:** report only. Fix nothing without the user's yes.
