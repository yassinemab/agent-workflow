# Question bank

These are lenses to look through, not a script. For each feature, pick the lenses that apply and turn them into **specific** questions about this feature, grounded in the code you read ("`Campaign.status` has no `PAUSED` state. What happens to scheduled steps when someone pauses?"). Never paste a generic question.

## Purpose and value
- What problem does this solve, for whom, and how do they work around it today? What breaks if we don't build it?
- What is the smallest version that solves the real problem? What can wait for v2?
- How will we know it worked after launch (a usage number, fewer support tickets, a metric)? Is it measurable with the data we already collect?
- Is there an existing feature this overlaps with, extends or contradicts?

## Users, roles and permissions
- Which roles can see it, use it, change it? What does everyone else see: hidden, disabled, or an error?
- Multi-tenant scoping: can any query, ID in a URL, or bulk action reach another workspace's or user's data?
- What happens to the feature's data when a user is removed, a workspace is deleted, a subscription ends or a trial expires?
- Are there admin or support needs (view, override, undo) that should be part of the scope?

## Inputs and data edge cases
- Empty / missing: no data yet, empty lists, null optional fields, a missing relation, a first-time user.
- Size: 0, negative, huge numbers, very long text, many items (pagination, bulk limits), large files.
- Format: unicode, emoji, leading/trailing whitespace, HTML/script in text, locale formats (decimal comma `1,5`, dates), timezones.
- Duplicates: same input twice, same name, same external ID. Is that allowed, merged or rejected?
- Validation: where does it happen (frontend for UX, backend always), and what exact error does the user see?

## State and lifecycle
- What states can the main object be in? Draw the state machine. Which transitions are allowed, and by whom?
- What happens to in-flight work when the parent object changes state (paused, archived, deleted, edited mid-process)?
- Can actions be undone? Soft delete or hard delete? What happens to dependent data?
- Editing after the fact: if the config changes, does it apply to existing items, new items only, or both?

## Concurrency and timing
- Double click / double submit, two users acting on the same object, a request retried after a timeout.
- A background job and a user editing the same row at the same time. Two job workers picking up the same item.
- Ordering: can events arrive out of order (webhooks, websocket messages, retries)? Does it matter?
- Time: month/year boundaries, DST, scheduled actions at a time that doesn't exist, clock skew, "now" in which timezone?
- Long-running work: what does the user see while it runs, can they leave the page, what happens if they start it again?

## External systems and side effects
- Which external calls does it make (email, LinkedIn, payments, LLMs, webhooks, third-party APIs)? Rate limits? Cost per call?
- What if the external call fails, times out, or succeeds but we crash before recording it? Is a retry safe (idempotency)?
- Must the side effect happen exactly once, at least once, or at most once? Which is acceptable for the user?
- Can testing trigger a real side effect? How is that prevented in dev?

## Scale and performance
- How many rows/items/users today, and in a year? (Check prod read-only if the profile allows it.)
- N+1 queries, missing indexes, unbounded queries, loading everything into memory.
- Quantified targets only where they matter: "p95 under X ms at N rows", "processes N items per minute".

## Failure, recovery and observability
- What does the user see for each failure? Is the message actionable?
- Can the system end up half-done? How is that detected and repaired (retry job, admin action, management command)?
- What needs logging or metrics so a bug in this feature can be debugged from production logs?

## Migration and rollout
- Existing data: does it need a backfill, a default, or a conversion? What about rows that don't fit the new rules?
- Is the migration safe while production is serving (table locks on large tables, renames, NOT NULL on big tables)?
- Old clients: does an open browser tab or a cached frontend break against the new API?
- Feature flag or gradual rollout needed? How is it rolled back, and does rollback lose data?

## UX and copy
- Loading, empty, error, partial, success and permission-denied states, each with its exact text.
- Every supported language; strings that run longer in other locales; mobile width.
- Is the user told what happened after an action (and what will happen next, for async work)?

## LLM features (with agent-harness)
- Which tier is enough: one call, a fixed workflow with one model step, or an agent that picks tools? What breaks if we go one tier lower?
- What does a wrong answer cost? Who sees it before it has an effect (a draft to approve, a confirmation step), and what can never be done without a person?
- Which numbers, IDs and dates must come from the database instead of the model?
- Which third-party text reaches the model (emails, web pages, documents)? What could an instruction hidden in it make the model do?
- Cost and latency budget per run, in numbers. Maximum steps and tokens.
- What makes an answer good? Write 10–20 eval cases with expected outcomes, and a pass threshold ("at least 18 of 20").
