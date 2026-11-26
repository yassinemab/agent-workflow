---
name: agent-harness
description: Build, extend or audit the harness around an LLM feature or AI agent. Covers choosing the right tier (single call, workflow, interactive agent, headless agent), the component checklist per tier, a fixed set of engineering standards, and a fixed audit report. Use this whenever the user builds or reviews an LLM feature, an agent loop, tool calling, an in-app AI assistant or chatbot with tools, an MCP integration, or a background or scheduled agent, or asks things like "review my agent", "is this production-ready", "what's missing in this harness", "how should I structure this AI feature", even if they never say "harness". Not for API or SDK syntax questions (use the claude-api skill or the provider's docs) or for prompt wording alone.
---

# Agent harness

A harness is everything around the model that turns API calls into a working feature: the loop, context assembly, tools, state, safety, the model client and observability. The model is stateless. Almost every production failure of an LLM feature is a harness failure: a truncated answer treated as complete, a tool that writes twice, a number taken from a summary, a run nobody can replay.

The goal is **the smallest harness that fits the task**, built on a few standards that are never skipped. More components are not better. Each one costs code, latency and attention.

## Two modes

- **Build or extend:** follow "Step 0", then "Building or extending".
- **Audit an existing feature:** follow "Step 0" (to judge which tier the feature *should* be), then "Auditing".

If it is unclear which mode the user wants, a request that names existing code ("review", "check", "what's missing") is an audit. Everything else is a build.

## Step 0: choose the tier

| Tier | What it is | Pick it when |
|---|---|---|
| 1. Single call | One request, one response, often structured output | Classification, extraction, scoring, drafting a text |
| 2. Workflow | Fixed steps in code, the model only where there is real ambiguity | The order of steps is known in advance |
| 3. Interactive agent | The model chooses tools in a loop while a person watches | Each result changes what happens next, and the task is hard to specify up front |
| 4. Headless agent | An agent triggered by a schedule, queue, webhook or event, with nobody watching | Same as tier 3, but it runs in the background |

Start at the lowest tier that works and move up only with a stated reason. A workflow is cheaper, faster, easier to test and easier to audit than an agent. Many "agents" in the wild are better as a tier 2 workflow with one LLM step. Also weigh the cost of an error: if a mistake is hard to undo, prefer the lower tier, or add a confirmation gate.

State the chosen tier and the reason in one or two sentences before building or auditing.

## The standards

These apply at every tier where the component exists. They come from real failures, so each has a reason. When building, implement them first. When auditing, check each one with evidence.

1. **Check the stop reason before using the output.** A response cut off by the output limit (`max_tokens`, `length`) looks like a normal answer. A half-written tool call has incomplete arguments. A refusal has no usable content. Branch on the stop reason every time.
2. **Authorization and tenant scoping live in code.** The workspace, tenant or user comes from the session, never from the model's arguments or the prompt. A model can be talked into asking for another tenant's data. Code cannot.
3. **Writes that matter go through a gate, and are idempotent.** Propose-then-confirm, a human approval, or a risk or confidence threshold. The confirmation executes the proposal the server stored, never a payload the client sends back, so what runs is exactly what the user saw. Every write tool takes an idempotency key, so a retry never books, sends or pays twice.
4. **Tool output and third-party content are data, not instructions.** Say so in the system prompt, and enforce the important limits in code, because a prompt is not a security boundary. This includes what the interface renders: model output shown as markdown or HTML can leak data through prompt injection, for example an image whose URL carries workspace data and loads without a click. Render only safe elements, and treat external links and images from model output as untrusted.
5. **Store every step.** Per call: model, input and output token counts, cost, latency, stop reason. Per tool call: name, arguments, result (or a reference to it), and outcome. Without this, you cannot debug a bad run, replay it, or turn it into an eval case.
6. **Numbers come from systems of record.** Amounts, counts, dates and IDs are read from the database or API and checked by code. Never trust a number the model calculated or a number that only survives in a summary.
7. **Keep the prompt prefix stable.** Static content (instructions, tool definitions, reference material) first, dynamic content (time, user, page) last, so prompt caching works. Check that cache hits actually happen.
8. **Everything is bounded.** Maximum steps per run, a token or cost budget, a timeout on every external call, and truncation of large tool results with a hint on how to ask for less.
9. **Errors go back to the model in a form it can act on.** Unknown tool, invalid arguments, not found, rate limited: return a short message that says what to do instead, rather than crashing or returning a stack trace.
10. **One shared LLM client per project.** Model per feature from configuration, timeouts, retries with backoff on rate limits and server errors, fallback where it makes sense, and token and cost logging in one place. Not a new client with its own retry loop in every file.
11. **Evals before claims.** A fixed set of cases with expected outcomes, run on every change to the prompt, model or tools. Unit tests with a fake LLM client prove the plumbing works. Only evals tell you whether the answers are good.

## Component checklist per tier

`must` = needed for a working, safe feature at this tier. `should` = add it unless there is a clear reason not to. `skip` = not needed at this tier; adding it is over-engineering.

| Component | 1. Single call | 2. Workflow | 3. Interactive agent | 4. Headless agent |
|---|---|---|---|---|
| Agent loop | skip | skip (code orchestrates) | must | must |
| Context assembly | must | must | must | must |
| Tool layer | skip | should, if steps call tools | must | must |
| Context management | skip | skip | should (must for long conversations) | must |
| State and persistence | should (log each call) | must | must | must, durable and resumable |
| Safety and permissions | should (validate input and output) | must | must | must, with asynchronous approvals |
| Hooks and extensibility | skip | skip | should | should |
| Multi-agent | skip | skip | skip unless there is a concrete reason | skip unless there is a concrete reason |
| Model client | must | must | must | must |
| Observability | should | must | must | must, with alerts |
| Interface | n/a | n/a | must (streaming, approvals, interrupts) | must (triggers, review queue, notifications) |
| Evals | should | must | must | must |
| Durability (queue, workers, leases, resume) | skip | should for batch jobs | skip | must |

For what each component must do, typical mistakes and how to test it, read `references/components.md`. Read it when building a component you have not built before, or when an audit finding needs detail.

## Building or extending

1. **Find what exists first.** Search the project for LLM clients, agent loops, tool registries and MCP servers. Reuse and extend them instead of adding a parallel version. If every file creates its own client, propose the shared client (standard 10) as part of the work.
2. **Choose and state the tier** (Step 0).
3. **List the components** marked `must` for that tier, plus the `should` items you will include. Name the ones you skip and why in one line each.
4. **Build the smallest version that meets the standards.** Standards first, features second. For provider-specific API details (request shapes, stop reason names, caching syntax, SDK helpers), use the claude-api skill for Anthropic, or the provider's current documentation. Do not guess SDK signatures.
5. **Test in two layers.** Deterministic tests with a fake LLM client cover the plumbing: the loop ends, stop reasons are handled, invalid tool arguments return an error, tenant scoping holds, a write tool called twice with the same key writes once. A small eval set covers answer quality.
6. **Report** what was built, which components were deliberately skipped, and what is not verified yet.

## Auditing

Read-only. Do not run anything against production systems, and do not change code during an audit unless the user asks for fixes afterwards.

1. **Scope:** which feature, which files, which branch. If the feature lives on a branch, read that branch and its uncommitted changes. If it is behind the main branch, check what main changed in the same areas (migrations, shared tool registries, models), because a merge can break the feature or its safety assumptions.
2. **Find the core:** the LLM calls, the loop (if any), the tool registry, where results and conversations are stored, and the entry point (view, job, CLI).
3. **Judge the tier:** what tier the feature is, and what tier it should be. A mismatch in either direction is a finding.
4. **Map to components** using the checklist for the appropriate tier.
5. **Check each standard** with evidence.
6. **Write the report** using the template below.

Every finding needs evidence: a `path:line` reference or a short quote. If you could not verify something, say so instead of guessing. Separate "missing" from "not needed at this tier": recommending components the tier does not need is a mistake, not thoroughness.

### Audit report template

Use this structure:

```markdown
# Harness audit: <feature name>

**Scope:** <files, branch, commit>
**Tier:** <current tier> (appropriate: <tier>, because <reason>)
**Verdict:** <one sentence: is it safe and solid for its tier, and what holds it back>

## Most important fix
<The single change with the biggest impact on safety or correctness, why, and roughly how.>

## Standards
| # | Standard | Status | Evidence |
|---|---|---|---|
| 1 | Stop reason checked | Met / Partly / Missing / N.a. | path:line or quote |
...all 11...

## Components
| Component | Needed at this tier | Status | Evidence | Note |
|---|---|---|---|---|
...one row per component...

## Fixes, ranked
1. <fix> | impact: high/medium/low | effort: small/medium/large | <one-line how>
...

## Deliberately not needed
<Components or standards that do not apply at this tier, one line each with the reason.>

## Not verified
<What you could not check, and how to check it.>
```

Keep the report factual and short. One line per table cell. The ranked fixes are what the user will act on, so make each one concrete enough to start on.
