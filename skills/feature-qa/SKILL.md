---
name: feature-qa
description: End-to-end QA of one feature in the current project's web app. Reviews the feature's code for unhandled edge cases and bugs, then tests it live in the browser against the locally running app with three persona sub-agents (Sonnet, high effort) that each use the feature like a different kind of user, and writes a verified bug report. Project specifics (URLs, roles, languages, data-safety checks, side effects to avoid) come from the project profile, or are worked out from the code on first use. Use this whenever the user says "run qa", "run QA on X", "do a QA", "qa this", "qa the branch", or otherwise asks to QA, test, check, try out, stress-test or "break" a feature, page, flow or branch, asks whether a feature is ready to ship, or says things like "test the invoicing flow", "check this for edge cases", "run the personas on X", even if they don't mention personas or the browser. A bare "run qa" with no feature named means QA what was changed in the current conversation (not the whole branch).
---

# Feature QA

Three passes over one feature, each feeding the next:

1. **Code pass (you):** read the feature's code, list edge cases and suspected bugs.
2. **Live pass (3 persona sub-agents):** use the real, locally running app, each persona with a different mindset, and try to reproduce what the code pass suspected.
3. **Verdict (you):** check every persona claim against the code, then write one report.

The code pass is what makes the live pass worth the tokens: personas that know "the amount field is parsed with `parseInt`, try `1.5` and `1,5`" find real bugs; personas told "test invoicing" click around and report the happy path.

Do not fix anything during the run. The output is a report; fixing is a separate decision for the user.

Paths below starting with `~` are in the user's home folder. Expand them to absolute paths when you pass them to a sub-agent or a file tool.

## 0. Learn the project
Find the project profile (how profiles work: `~/.claude/project-profiles/README.md`):
```bash
REPO=$(basename -s .git "$(git remote get-url origin 2>/dev/null)" 2>/dev/null)
[ -n "$REPO" ] || REPO=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
ls "$(git rev-parse --show-toplevel)/.claude/project-profile.md" ~/.claude/project-profiles/"$REPO"/profile.md 2>/dev/null
```
Read it (the repo's `.claude/project-profile.md` wins). Without a profile, work out the following from the code, config and README before going on, and write it down; you need all of it for the briefs:
- **Stack and layout:** where backend and frontend code live, where routes are defined, the base branch.
- **Running it:** frontend and API URLs (dev server config, `package.json` scripts, `.env*`, docker-compose), and how sign-in works.
- **Data safety:** which database and external services the local app talks to, and how to prove it's local or dev, not production (env files, connection settings, open tunnels).
- **Users and permissions:** roles and other states that change what a user can see or do.
- **Languages:** locales, where the strings live, any i18n check script.
- **External side effects:** email, messages, payments, webhooks, invoices, third-party APIs the feature can trigger.

## 1. Pin down the feature

The feature comes from the skill arguments or the conversation.

**No feature named ("run qa", "test my stuff"): test what this conversation changed, not the branch.** The branch and the working tree can hold unfinished work from other conversations that the user doesn't want tested yet.
- List the files this conversation created or edited: your own Edit/Write calls, plus changes the user made and discussed here. Write the list down before going further; it is the scope.
- Read their current changes: `git diff -- <files>` for tracked files, and the full content of new ones.
- A file can also hold changes that this conversation didn't make (another session working in the same checkout). Test only the parts this conversation changed, and leave the rest alone.
- If this conversation hasn't changed any files (e.g. a fresh session), ask which feature to test instead of guessing.
- Use the whole branch only when the user asks for it ("qa the branch"): `git diff <base>...HEAD`, with the profile's base branch, otherwise `origin/HEAD` after checking it's where recent merges land.

Then find:
- **Code:** backend (views/controllers, serializers, models, jobs) and frontend (pages, components, stores, data-fetching hooks, i18n keys). Read the files in full, not just the diff: many bugs live where new code meets old code.
- **Where it lives in the UI:** the route(s) and how a user reaches them (menu, button, URL).
- **Who uses it:** which roles can see or do what; permission gaps are a common bug.
- **External side effects** the feature can trigger. Personas must stop short of those (see the persona brief).
- **The spec, if there is one** (from `scope-feature`, in the profile's report folder or `~/.claude/reports/<repo>/scope-feature/`). Every acceptance criterion with a UI check becomes a charter in step 4, and the report says per criterion whether it was reproduced as passing in the running app.

## 2. Code pass: edge cases and bugs

Work through the code with these lenses. Write down each finding with `file:line`, what goes wrong, and how a user would trigger it in the UI.

**Edge cases (inputs and states the code may not handle):**
- Empty / missing: no data yet, empty lists, null fields, optional relations missing, first-time user.
- Size: very long text, 0, negative, huge numbers, many items (pagination), decimals and locale formats (decimal commas like `1,5`, thousands separators, currency signs).
- Text: unicode, emoji, leading/trailing spaces, HTML/script in input, every locale (missing i18n keys show raw keys).
- Time: timezones, month/year boundaries, dates in the past, DST, `null` dates.
- Concurrency and repetition: double-submit, two tabs, refresh mid-flow, back button, stale data after another user edits.
- Permissions: a lower role hitting an admin-only endpoint, another tenant's or user's IDs in the URL, deleted or deactivated users, expired trials or subscriptions (whatever the profile lists).
- Failure: API error or timeout. Does the UI show an error, spin forever, or silently drop the change?

**Bugs (code that is wrong regardless of input):**
- Frontend and backend disagree on field names, types, enums or status codes.
- Missing `await`, unhandled promise rejections, stale caches not invalidated after a mutation, effects with wrong dependency arrays.
- Queries not scoped to the tenant or user, N+1 queries, missing transactions around multi-step writes, off-by-one in ranges and pagination.
- Error paths that swallow exceptions or return success on failure.

Rank findings: **confirmed** (you can see it is wrong from the code alone) vs **suspected** (needs the live pass to confirm). Suspected findings become test charters for the personas.

## 3. Preflight

Check before spawning anyone, so three agents don't each hit the same wall:
- **The app runs.** `curl` the frontend and API URLs. If one is down, tell the user and stop. Don't start dev servers in the background on your own unless the profile says to; the user usually has them running in their own terminals.
- **The data is not production.** Run the profile's data-safety checks, or the ones you worked out in step 0. Personas create and edit data. If the local app talks to a production database or production services, or you can't tell, stop and ask the user.
- **Signed in.** Open the app in the browser and check you're signed in with a role that can use the feature. If not, ask the user to sign in. Don't type passwords yourself unless the user gave you test credentials for this local app.

**Which browser:** use the built-in browser pane (`mcp__Claude_Browser__*`) when it exists, otherwise the browser tools this session has (Claude in Chrome only if the user asks for it). The macOS computer-use tools only get read access to browsers, so they can't click through a web app.

**Keep the browser pane visible.** Ask the user to leave it showing during the run. A hidden pane freezes the page's timers and promises, so debounced inputs, scripts and navigation stall or time out.

**One record per persona in one-way flows.** If the feature moves a record through states that can't be undone (submit → approve → send), one persona finishing a step closes it for the others. Before spawning, create a separate record for each persona in the local database, for example through the framework's shell and the feature's own service functions, and list them under test data in the report.

## 4. Spawn the three personas

Use the profile's personas when it has them. Otherwise pick three that fit the feature and the product's real users. The default trio covers most features:

| Persona | Mindset | Looks for |
|---|---|---|
| **New user** | First week, non-technical, reads every label, follows the obvious path, gets confused easily | Unclear copy, dead ends, missing empty states, confusing errors |
| **Power user** | Uses the app all day, moves fast, double-clicks, opens things in new tabs, uses back/refresh mid-flow, has lots of data | Double-submit, stale data, broken navigation, slow pages, pagination and sorting bugs |
| **Edge-case hunter** | Deliberately tries to break it: empty, huge, negative, emoji, `<script>`, dates on boundaries, other tenants' IDs in the URL | Validation gaps, crashes, 500s, permission leaks, the suspected bugs from step 2 |

Give each a first name and a role that fits the product. Adapt to the feature: for an admin-only feature all three are admins with different habits; for a permissions-heavy feature, make one a user who should *not* be able to do things.

Split the step 2 charters across personas by fit, so every suspected bug is assigned to someone. Each persona also gets free time to explore in character, which catches what the code pass missed.

Spawn all three **in one message** so they run in parallel, with:
- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `effort`: `high`
- `prompt`: the persona brief from [references/persona-brief.md](references/persona-brief.md), filled in.

**Parallel browser use:** all three share the browser, its cookies and its `localStorage`, so they are signed in as the same user and see the same UI language. Each persona must create its own tab and pass that tab's id on every browser call. None of them may sign out, switch accounts or change the language, because that would flip the other personas' tabs. If a persona needs a *different* account or role, run that persona after the other two finish, and have the user sign in as that account first. If parallel runs keep colliding (tabs closed, wrong tab acted on), rerun the personas one at a time.

**Language pass (you, after the personas finish; only if the app has more than one locale):** run the project's i18n check script if there is one. Then switch the UI to the locale most users use, or the one with the longest strings if that isn't English. Walk the feature's pages and dialogs once with the page text, and look for raw keys (`invoice.form.title`), untranslated text and text that overflows. Switch back to the language you found.

## 5. Verify the persona reports

Persona reports are claims from a smaller model, not facts. For each reported bug:
- Find the code that causes it. If you can point to the line, it is **confirmed**.
- If the report is unclear or contradicts the code, reproduce it yourself in the browser before including it.
- Drop "bugs" that are the persona misunderstanding the feature, and say so in a short "not bugs" list so the user sees they were considered.
- Merge duplicates found by several personas (that's a signal of severity, keep the note).

Also mark which step 2 charters were **reproduced**, **not reproduced** (the code is fine or the persona couldn't reach it), or **not tested**.

## 6. Report

Write the report to the profile's report folder, or by default `~/.claude/reports/<repo>/feature-qa/`, as `<feature-slug>-<YYYY-MM-DD>.md`. Give the user a short summary in chat with the path.

```markdown
# QA: <feature> — <date>

## Verdict
<Ready / Ready with fixes / Not ready>, one or two sentences why.

## Bugs
| # | Severity | What happens | How to reproduce | Cause (file:line) | Found by |
Severity: Blocker (data loss, wrong money, security, crash on main path) · Major (feature broken for some users or inputs) · Minor (works, but wrong/ugly) · Copy (text, translation).

## Unhandled edge cases
Inputs/states the code doesn't handle that no persona hit, with file:line and the input that would trigger it.

## Charters from the code pass
| Suspected issue | Persona | Result (reproduced / not reproduced / not tested) |

## UX notes
Confusing flows and copy, mainly from the new-user persona.

## Not bugs
Persona reports that turned out to be expected behavior, one line each.

## Test data created
Records the personas created (all prefixed `QA-`), so the user can clean them up.
```

Keep the report about the feature. Don't pad it with things that work fine; one line in the verdict ("happy path works in every locale") is enough.

**No profile yet?** Offer to save what you worked out in step 0 as `~/.claude/project-profiles/<repo>/profile.md` (template in the README there), so the next run skips that step. Write only what you verified.
