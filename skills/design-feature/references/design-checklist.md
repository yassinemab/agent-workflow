# Design checklist

Run every item against the design before showing it to the user. Each "no" is either fixed or written into the design's "Known risks and weak points" with the reason it's acceptable.

## State and data (ACID)
- **Atomicity:** is each user action one transaction? Is anything written outside it that could leave a partial state?
- **Consistency:** is every invariant enforced by the database where it can be (unique, foreign key with the right `on_delete`, NOT NULL, check constraint), not only by `if` statements in application code?
- **Isolation:** for every race in the spec (double click, two users, retries, concurrent jobs), which guard prevents it: a unique constraint, a row lock (`SELECT … FOR UPDATE`), a conditional update (`UPDATE … WHERE status = 'x'`) or an idempotency key? Is there any check-then-act without one?
- **Durability:** are external side effects and job enqueues deferred until after commit (e.g. Django's `transaction.on_commit`, or an outbox table)? Are they idempotent when retried?
- **Migrations:** is each migration safe while production keeps serving traffic (locks on large tables, NOT NULL on big tables, renames and drops in two deploys)? Is there a backfill for existing rows, and can it be rolled back without losing data?

## Structure (SOLID, cohesion, coupling)
- **Single responsibility:** does each new module, class or component have one reason to change? Request handlers parse and authorize, services hold business rules, serializers or presenters shape output.
- **One home per rule:** is any business rule duplicated between frontend, view, serializer, service and job?
- **Cohesion:** do the things that change together for this feature live together?
- **Coupling:** does the new code reach into another module's internals, or chain through objects (`a.b.c.d`)? Does a change elsewhere risk breaking it?
- **Abstractions:** is every interface, base class and adapter justified by a real second implementation or a real boundary (external provider, test seam)? One adapter is a hypothetical seam; two is a real one.
- **Deep modules:** does each new module hide real complexity behind a small interface? Delete-test: if you deleted it and inlined its body, would anything get harder? If not, it's a pass-through.
- **Functional core:** are the business rules pure functions, with database, API and LLM calls at the edges?

## Reuse and simplicity (DRY, KISS, YAGNI)
- **Reuse:** did you search for an existing helper, client, component or pattern before designing a new one? Name the files.
- **Wrong abstraction:** is a shared abstraction being forced onto two things that only look alike?
- **Simplest design:** is there a simpler design that meets every acceptance criterion? Does every table, field, flag, option and layer map to a criterion?
- **Consistency:** does the design follow the codebase's existing patterns? If it deliberately doesn't, is there an ADR, and a plan for the old usages?

## Contract and behavior
- **API:** are request and response shapes, status codes and error bodies consistent with the rest of the codebase?
- **Types:** are the payloads typed on both ends, with the backend and frontend types in agreement?
- **UI states:** loading, empty, error, partial, success and permission-denied, each with its exact text or i18n key, in every supported language.
- **Feedback:** is the user told what happened after an action, and what happens next for async work?

## Failure and security
- **Failure modes:** what happens when each external call fails, times out or succeeds after we crash? What does the user see? How does an operator find and repair a half-done state?
- **Authorization:** who can call each entry point, and how is tenant/workspace scoping enforced on every query?
- **Input:** where is input validated (at the boundary, failing fast), and what exact error comes back?
- **Rendering:** is any user- or third-party-supplied content rendered as HTML or markdown? How is it sanitized?

## Testability
- Can every acceptance criterion be checked by an automated test at the right level: unit for rules, integration for transactions, races and permissions, UI for flows?
- Do the tests go through public seams, so they survive internal refactors?
- Are mocks limited to system boundaries (network, LLM, payment, email, clock)?
