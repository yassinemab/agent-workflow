# Harness components in detail

Read the section for the component you are building or auditing. Each section has: what it does, the must-haves, common mistakes, and how to test it.

Contents:
1. Agent loop
2. Context assembly
3. Tool layer
4. Context management
5. State and persistence
6. Safety and permissions
7. Hooks and extensibility
8. Multi-agent
9. Model client
10. Observability
11. Interface
12. Evals
13. Durability (headless agents)

---

## 1. Agent loop

**What it does:** calls the model, branches on the stop reason (run tools, finish, continue after a pause, handle truncation or refusal), and repeats until there is a final answer or a limit is hit.

**Must-haves:**
- Branch on every stop reason the provider can return, not just "tool call or not".
- A maximum number of rounds. On the last round, stop offering tools so the model has to answer.
- A token or cost budget per run, and a timeout per call.
- Run parallel tool calls and return all results together, linked by call ID.
- Stop cleanly when the user cancels or disconnects.

**Common mistakes:**
- Treating every response without a tool call as a finished answer, so truncated answers are shown as complete.
- Running a tool call whose arguments were cut off by the output limit.
- No round limit, so a confused model loops until the budget or timeout kills it.

**Test:** with a fake client that returns scripted responses: a truncated response, a refusal, a tool call followed by an answer, a model that calls tools forever (the loop must stop at the limit).

## 2. Context assembly

**What it does:** decides what the model sees on each call: instructions and role, project or customer instructions, the tool list, the relevant history or a summary, dynamic context (time, user, language, current page), and retrieved facts.

**Must-haves:**
- Static content first, dynamic content last, so the prefix can be cached.
- Dynamic facts the model needs to answer correctly: current date and time zone, user language, which object the user is looking at.
- Only what is needed. More context is not free: it costs tokens and can distract the model.

**Common mistakes:**
- A timestamp or user name at the top of the system prompt, which breaks caching on every call.
- Dumping a whole knowledge base into every request instead of an index plus retrieval on demand.

**Test:** snapshot the assembled request for a fixed input and check its order and contents. In production, check that cache hit tokens are above zero on repeated calls.

## 3. Tool layer

**What it does:** keeps the registry of tools from all sources (own code, MCP servers, provider tools), passes their definitions to the model, routes each call to the right place, validates arguments, runs the tool and formats the result.

**Must-haves:**
- Validate arguments against the schema, not only "is it valid JSON".
- Clear names and descriptions, including what the tool returns and its limits.
- Separate read tools from write tools, with an explicit flag on each tool (for example `writes=True`) rather than relying on naming. Filter on that flag wherever a tool set is reused, so a write tool added elsewhere never reaches an agent without a gate. Write tools are idempotent and gated (standard 3).
- Truncate large results and say how to ask for less.
- Rate limits on expensive tools.
- Scope every tool to the tenant from the session (standard 2).

**Common mistakes:**
- Many overlapping tools, so the model picks the wrong one.
- Tools that take names where IDs are needed, so lookups silently miss.
- Returning raw exceptions or huge payloads to the model.

**Test:** call each tool directly with valid, invalid and out-of-scope arguments (another tenant's ID must fail). Check that the same write with the same idempotency key happens once.

## 4. Context management

**What it does:** keeps long runs within the context window and the budget: counting tokens, trimming old tool results, compacting older turns into a summary, and moving work into sub-agents with their own context.

**Must-haves:**
- Know how close each call is to the limit.
- A strategy before you hit the limit: trim tool results first (cheap, loses little), summarize older turns second.
- Material facts (amounts, IDs, decisions) kept in structured state, not only in a summary (standard 6).

**Common mistakes:**
- Sending the full history forever, so cost grows with every turn and quality drops.
- Compacting a little on every turn, which breaks the prompt cache each time.

**Test:** run a long scripted conversation and check that the context stays under the limit and that key facts survive compaction.

## 5. State and persistence

**What it does:** stores what the harness needs outside the context window: transcripts, per-step records, working state (plan, pending approvals), checkpoints, and long-term memory.

**Must-haves:**
- An append-only record of every step (standard 5), written as the run goes, not only at the end.
- Enough to replay a run: the inputs, the tool calls with arguments and results, and the model used.
- Long-term memory, if any, kept separate in concept: it is curated and can be wrong, while the transcript is a record of what happened.

**Common mistakes:**
- Storing only the final answer text, so a bad answer cannot be debugged.
- Storing tool names but not arguments and results.

**Test:** run a conversation, then rebuild the exact sequence of model and tool calls from storage alone.

## 6. Safety and permissions

**What it does:** decides what the agent may do: allowed tools and actions, approvals, sandboxing, keeping secrets out of the context, and defending against prompt injection. Optionally a reviewer model that judges risky actions.

**Must-haves:**
- Tenant and user scoping in code (standard 2).
- Gates on consequential writes (standard 3): propose-then-confirm, an approval, or a risk threshold.
- Secrets and credentials never in the model's context. A separate layer adds them to outgoing calls.
- Third-party content treated as data (standard 4).

**A reviewer pattern worth knowing:** judge each risky action on two axes, intrinsic risk (how bad if it goes wrong, how reversible) and authorization (did a trusted source, the user or the policy, ask for exactly this). Derive allow, escalate or deny from fixed thresholds. Only trusted sources can establish authorization; tool output and documents never can. A cheap check on every step can decide when the expensive review is needed.

**Common mistakes:**
- Relying on the system prompt for safety ("never archive without asking") without a gate in code.
- Gates so strict that users approve everything without reading.

**Test:** prompt-injection cases (a tool result that says "ignore your instructions and do X"), cross-tenant attempts, and a write without confirmation. All must fail safely.

## 7. Hooks and extensibility

**What it does:** runs your own code at fixed moments: before a tool call (can block it), after a tool call, when a prompt is submitted, when a run ends, before or after compaction. Also plugins, skills and commands that add behaviour without changing the core.

**Must-haves (when present):** a pre-tool hook can block and returns a reason the model can act on. Hooks have timeouts.

**Common mistakes:** putting core safety in an optional hook that can be switched off.

**Test:** a hook that blocks a specific call, and a hook that times out. The run must handle both.

## 8. Multi-agent

**What it does:** runs sub-agents for separate tasks, each with its own context, often on a cheaper model, and collects their reports.

**When it is worth it:** a sub-task needs a lot of reading whose details the main agent will not need afterwards, or independent sub-tasks can run in parallel.

**Common mistakes:** splitting work into agents when one loop would do, which adds cost, latency and coordination bugs. Sub-agents that hang with nobody noticing.

**Test:** a sub-agent that fails or times out. The parent must notice and recover or report.

## 9. Model client

**What it does:** talks to one or more providers: model selection, timeouts, retries, streaming, fallback, caching settings and usage reporting.

**Must-haves:**
- One shared client per project (standard 10).
- Model per feature from configuration, so it can change without a code change.
- Timeouts, and retries with backoff only on retryable errors (rate limits, server errors, connection failures), never on bad requests.
- Token usage (including cache reads and writes) logged per call.

**Common mistakes:** a client per file with different retry rules. Retrying a request that will always fail. Hardcoded model names spread through the code.

**Test:** fake transport errors (429, 500, timeout, 400) and check which are retried and how often.

## 10. Observability

**What it does:** makes runs visible after the fact: a trace per run with a span per model and tool call, tokens, cost and latency, plus logs and metrics.

**Must-haves:**
- A trace or structured log per run that links all its steps.
- Cost and latency per feature and per tenant.
- For headless agents: alerts on error rates, cost spikes and stuck runs.

**Common mistakes:** free-text log lines that cannot be joined into a run. No cost tracking until the bill arrives.

**Test:** run a conversation and answer from the traces alone: which tools ran, how long each step took, and what it cost.

## 11. Interface

**What it does:** connects the harness to people or systems: a chat UI with streaming, tool activity and approval cards, an IDE or CLI, or for headless agents the triggers, a review queue and notifications.

**Must-haves (interactive):** streaming, visible tool activity, approvals the user can understand, a way to stop a run.
**Must-haves (headless):** a clear trigger, a review queue for escalations, a report or notification when a run finishes or fails.

**Must-haves (both):** render model output safely. Markdown or HTML from the model must not load external images, scripts or iframes, and external links should be visibly external or limited to known hosts. A prompt injection in data the model read can otherwise turn the answer into a data leak.

**Common mistakes:** approval cards that do not show what will actually change. A confirm endpoint that executes whatever the client sends instead of the stored proposal. A markdown renderer with default settings for model output. Errors shown in the wrong language or as raw codes.

## 12. Evals

**What it does:** measures answer quality on a fixed set of cases, so changes to the prompt, model or tools can be compared.

**Must-haves:**
- 20 to 100 real or realistic cases with expected outcomes, including the hard ones.
- Deterministic graders where possible (exact values, required facts, forbidden actions); an LLM grader only for what cannot be checked by code, calibrated against human labels.
- Scores per slice (type of question, language, tenant size), not only one average.
- Run on every change, and add every production failure as a new case.

**Common mistakes:** only unit tests with a fake client, which prove the plumbing but nothing about answer quality. A score that goes up while users get worse results because the cases are too easy or stale.

## 13. Durability (headless agents)

**What it does:** makes background runs survive crashes and scale: a job queue, workers, leases so two workers never take the same job, checkpoints, resume after a crash, and retries with backoff for failed jobs.

**Must-haves:** idempotent steps (a resumed run must not repeat side effects), a lease or lock per job, bounded work per run, a heartbeat so stuck runs are visible.

**Test:** kill a worker mid-run and check that the job resumes without repeating a write.
