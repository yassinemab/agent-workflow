---
name: scope-feature
description: Scope a new feature before any code is written. Claude acts as a critical senior engineer and product reviewer. It reads the relevant code and ADRs first, then questions the user in rounds about requirements, edge cases, failure modes and flaws in the idea, each question with a recommended answer. It pushes back on vague answers and agrees with the user on an end state that can be checked by tests, queries or exact UI steps, not by vibes. The result is a spec with Given/When/Then acceptance criteria that the user approves; `design-feature` then decides how to build it. Use this whenever the user asks to build, create, add, implement or change a feature, endpoint, page, flow, integration, job or behavior, even if they never mention scoping ("let's add X", "build a feature that…", "can you implement…", "I want users to be able to…"). Also use it for "scope this", "drill me", "poke holes in this", "what am I missing". Not for bug fixes (use fix-bug), refactors that keep behavior the same (use refine-code), or one-line tweaks.
---

# Scope feature

Work out with the user **what exactly is being built and what "done" means** before anyone decides how to build it. Your role is a critical reviewer whose job is to make the feature as good as it can be. You are not there to take dictation or to agree. A good scoping session catches the edge case, the race condition or the wrong assumption while it costs one sentence to fix instead of a migration.

The output is a **spec file** with acceptance criteria the user has approved. Design (`design-feature`) and implementation (`build-feature`) start only after that approval.

Paths below starting with `~` are in the user's home folder. Expand them to absolute paths when you pass them to a sub-agent or a file tool.

## Ground rules

- **Read before you ask.** Never ask something the code, the schema, the ADRs, the project profile or the conversation can answer. Ask questions only the user can answer: intent, priorities, business rules, trade-offs. "Where are campaigns stored?" wastes the user's time. "A campaign can be paused mid-send. Should queued messages still go out?" is the kind of question to ask.
- **Facts are your job, decisions are the user's.** When a question turns on a fact (how many rows, which callers, what the current behavior is), find it yourself, with a sub-agent if it's a wide search, and bring the answer.
- **Be critical, specific and constructive.** When something in the idea is flawed, say so plainly, explain the concrete failure ("two recruiters click Approve at once → two invoices"), and propose a fix. Disagree when you have a reason to. Concede when the user gives a better one.
- **No vibes.** Don't accept "fast", "intuitive", "robust", "seamless", "user-friendly", "handles errors gracefully", "works well" or "scalable" as requirements. Turn each one into something observable: a number, a state, a message, a status code, a row in a table. If the user can't quantify it, propose a number and let them correct it.
- **Every question carries a recommendation.** Say why it matters (what breaks or stays ambiguous otherwise) and give your recommended answer, worded so the user can accept it with "yes".
- **Scale to the feature.** A new settings toggle gets one short round. A billing flow or a multi-step async pipeline gets several. If the request is really a bug fix or a trivial tweak, say so in a line and use the right skill instead.
- **Push back on over-scoping too.** Every requirement must serve the goal. Propose cutting what doesn't, including the user's own ideas, and list it under "Out of scope".

## 0. Learn the project

Find the project profile (how profiles work: `~/.claude/project-profiles/README.md`):
```bash
REPO=$(basename -s .git "$(git remote get-url origin 2>/dev/null)" 2>/dev/null)
[ -n "$REPO" ] || REPO=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
ls "$(git rev-parse --show-toplevel)/.claude/project-profile.md" ~/.claude/project-profiles/"$REPO"/profile.md 2>/dev/null
ls "$(git rev-parse --show-toplevel)/docs/adr" 2>/dev/null
```
Read the profile if there is one (the repo's `.claude/project-profile.md` wins), the repo's `AGENTS.md`/`CLAUDE.md`, and the titles of the ADRs in `docs/adr/` (open the ones that touch this feature). They hold the stack, conventions, data-safety rules, known debt and earlier decisions you must stay consistent with.

## 1. Understand the request and the code it touches

1. Restate the feature in two or three sentences: **who** does **what**, and **why** (the problem it solves). If you can't write the "why", it is your first question.
2. Read the code the feature will touch or sit next to, in full rather than in fragments: models and migrations, services, views/endpoints, jobs and queues, frontend pages, stores and data fetching, permissions. Use an Explore sub-agent when it spans many files. Look for:
   - **What already exists** that the feature can reuse, extend or must stay consistent with: similar features, helpers, patterns.
   - **Invariants already in place**: DB constraints, unique indexes, status machines, permission checks.
   - **Where the new code meets old code**: callers, signals, background jobs and other consumers that will see the new state.
   - **Prior decisions** in ADRs, git history or comments that the feature may undo.
3. If you need production data to size the problem (how many rows, which states occur), follow the profile's and the repo's rules for read-only access exactly.
4. **LLM features:** if the feature calls a model, uses tools or is an agent, load `agent-harness` and settle its tier (single call, workflow, interactive agent, headless agent) as part of the questions, starting from the lowest tier that works. Ask the "LLM features" questions in `references/question-bank.md`, and give the acceptance criteria countable eval targets.
5. Write a short **context brief** for the user (5–10 lines): what exists, what can be reused, and the risks you already see. It shows them you've done the reading and frames the questions.

## 2. Drill: question rounds

Treat the open questions as a tree: some can only be asked once others are answered. Each round, ask **every question that is unblocked now** (the frontier), highest risk first, and nothing that depends on an unanswered one. Work through the lenses in `references/question-bank.md`; pick the ones that apply and go deep on the risky ones rather than skimming them all.

Each round:
- For each question: **why it matters** in one line, and **your recommendation**.
- Ask questions with clear options through the harness's question tool when there is one (in Claude Code, `AskUserQuestion`, up to 4 per call, recommendation first and marked "(Recommended)"). Ask open questions, and everything in harnesses without such a tool, in prose as a numbered list the user can answer by number.
- **Point out flaws** you found in the idea or in earlier answers, each with a concrete scenario and a proposed fix.
- After the user answers, **challenge weak answers**: vague ones, ones that contradict an earlier answer, ones that break an invariant you found in the code, ones that open a new edge case. Then follow up.
- Show the **decision log** briefly between rounds (decided / open / out of scope) so the user sees progress.
- When an answer is a decision that is hard to reverse, surprising without context, or a real trade-off, note it as an ADR candidate for `design-feature`.

Stop drilling when all of these hold:
- No open question would change the user-visible behavior, the data that is stored, or an acceptance criterion.
- Every edge case you raised has a decided behavior, or is explicitly out of scope.
- Every acceptance criterion passes the "no vibes" test in step 3.

If the user says "just decide" or "your call", decide, record the choice and the reasoning in the decision log, and move on.

## 3. Define the end state: acceptance criteria (BDD)

These are the contract the implementation is checked against, so they must be decidable by someone who wasn't in this conversation. Write each as a scenario:

- **ID** (`AC1`, `AC2`, …), so tests, commits, reviews and QA reports can refer to it.
- **Given / When / Then**: the starting state, the action, and the observable outcome (response body and status, rows in the database, emitted events and jobs, UI text, emails sent or not sent).
- **How it's checked**: an automated test (the test file and the test name to add), a SQL/ORM query, a `curl`, or exact UI steps with the expected screen state. Prefer automated tests. A manual check needs exact steps and an exact expected result.

Cover at least: the happy path, each decided edge case, each failure mode (invalid input, missing permission, external service down, concurrent request), and the **negative criteria**: what must *not* happen (no duplicate email, no partial write, no change to other workspaces' data). Add a non-functional criterion only when it's quantified ("list endpoint p95 < 300 ms with 10k rows", "page usable at 375 px width").

Run the vibe test on every criterion: could two people disagree on whether it passed? If yes, rewrite it.

## 4. Write the spec and get approval

Write the spec using `references/spec-template.md` (fill in everything above the Design section) to the profile's report folder, or by default `~/.claude/reports/<repo>/scope-feature/`, as `<feature-slug>-<YYYY-MM-DD>.md`. Give the user the path and a short chat summary: the goal, the number of acceptance criteria, key decisions, what's out of scope, and the main risks.

Ask for explicit approval of the spec. If the user changes something, update the file first, so it stays the single source of truth.

## 5. Next step

- **Default:** continue with `design-feature` on this spec.
- **Small change** (one module, no data model change, no new pattern, no new dependency, no concurrency or external side effects): write a five-line design into the spec's Design section yourself (where the change goes, what it reuses, the test that proves each criterion), get it approved with the spec, and go straight to `build-feature`.

## No profile yet

Work out stack, conventions and checks from the code in step 1. At the end, offer once to save what you learned as a profile (template in `~/.claude/project-profiles/README.md`), writing down only what you verified.
