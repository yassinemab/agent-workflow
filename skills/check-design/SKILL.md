---
name: check-design
description: UI/UX design review of a page, feature or branch in the current project's web app. Checks how consistent, coherent and good the interface is against the project's own design system (its tokens, theme and shared components, plus the project profile's design notes when there are any) and a merged checklist from six design skills (Anthropic frontend-design and webapp-testing, ui-ux-pro-max, impeccable, ui-skills, Vercel web design guidelines). It combines a drift scan of the code with an unanchored review of the running app in the browser, and writes a scored report with prioritized, evidence-backed fixes. Use this whenever the user says "check design", "design review", "review the UI/UX", "is this consistent", "does this follow our design system", "polish check", "how does this page look", or asks whether a screen or feature looks and feels right, even if they don't say "design system". With nothing named it reviews what the current conversation changed, not the whole branch. Not for functional testing (use feature-qa) or code quality (use refine-code).
---

# Check design

Judge one surface (a page, a flow or a feature's screens) on three questions:
1. **Consistent:** is it on the project's design system, and does it match the rest of the app?
2. **Coherent:** is the hierarchy clear, does the flow make sense, do the words and states fit together?
3. **Good:** is it usable and accessible, does it handle real content and every state, and is it free of generic "AI slop"?

The output is a report. Don't edit product code during the review; fixing is a separate step the user decides on.

Paths below starting with `~` are in the user's home folder. Expand them to absolute paths when you pass them to a sub-agent or a file tool.

## 0. Learn the project
1. **Find the project profile** (how profiles work: `~/.claude/project-profiles/README.md`):
   ```bash
   REPO=$(basename -s .git "$(git remote get-url origin 2>/dev/null)" 2>/dev/null)
   [ -n "$REPO" ] || REPO=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
   ls "$(git rev-parse --show-toplevel)/.claude/project-profile.md" ~/.claude/project-profiles/"$REPO"/ 2>/dev/null
   ```
   Read `profile.md` (or the repo's `.claude/project-profile.md`, which wins), and `design-system.md` and `design-scan.json` next to it if they exist.
2. **Find the design system as code.** That is the source of truth, so re-read it every review: the theme config (`tailwind.config.*`, CSS custom properties, a theme file for MUI/Chakra/styled-components…), the global stylesheet with component classes, and the shared component folder (buttons, cards, modals, toasts, badges, empty states, skeletons). If the design notes disagree with the code, the code wins; say so in the report.
3. **No design notes?** Write a short working version yourself before reviewing, from the code and 2–3 representative screens: palette and what each colour means, type scale, radius and spacing scale, the components to reuse, the icon set, the product's character (a dense all-day work tool and a marketing site deserve different judgments), and which locales exist. Use it as the "design system" in the briefs below, and keep it for the report.
4. Read [references/checklist.md](references/checklist.md): the 75-point checklist and P0–P3 severity. Where it disagrees with the project's design notes, the notes decide.

Also take from the profile (or work out): the app's URL, how to sign in, the locales, the language most users use, and where reports go.

## 1. Scope
- A named page, route or feature: find its route(s) in the router and layouts, and its components.
- **Nothing named: what this conversation changed, not the branch.** The branch and the working tree can hold unfinished work from other conversations.
  - List the frontend files this conversation created or edited (your own Edit/Write calls, plus changes the user made and discussed here).
  - Read their changes with `git diff -- <files>`.
  - Review the screens they render, judging mainly what changed.
  - If this conversation changed no frontend files, ask which screen to review.
- "this branch": only when the user asks for it. Diff against the profile's base branch (otherwise `origin/HEAD`, after checking it's where recent merges land): `git diff <base>...HEAD --stat -- <frontend dir>` plus uncommitted changes, and the screens they render.
- List the **states** each screen can be in: empty, loading, populated, long or odd content, validation error, server error, no permission, success, every dialog or confirm step. A design review that only sees the happy path misses most problems.
- Pick 1–2 **neighbouring screens** that do something similar, to compare consistency with.

## 2. Two independent passes
Run them separately so neither anchors the other. The live reviewer must not see the scan output or your code notes before it reports (impeccable's rule).

### A. Live review (fresh sub-agent)
Check that the app's URL responds and that the browser is signed in with a role that can see the screens. If not, ask the user to sign in. Don't start dev servers in the background unless the profile says to; the user usually runs them. Use the built-in browser pane (`mcp__Claude_Browser__*`) when it exists, otherwise the browser tools this session has. If you use the pane, ask the user to keep it visible: a hidden pane freezes timers and can stall screenshots and scripts.

Then spawn a `general-purpose` sub-agent (`model: sonnet`) with this brief, filled in:

> You are a senior product designer reviewing part of <product: one sentence on what it is and who uses it, and its character, e.g. "an operate tool used all day: clarity and consistency beat flair">. Review these screens and states: <URLs, how to reach each state, and the neighbouring screens to compare with>. First read <absolute path of the project's design notes, or paste your working version from step 0> and `<absolute path>/check-design/references/checklist.md`.
>
> Use <browser tools; for the built-in browser: `mcp__Claude_Browser__*`, load with ToolSearch if deferred>. Create your own tab and use only that tab (`tabs_create`, then its `tabId` on every call). Don't sign out or change account settings; don't submit, approve, send or delete anything real. Opening dialogs and confirm steps and then backing out is fine. Before judging a screen, let it settle: no pending requests, skeletons gone (webapp-testing's "wait for networkidle, then inspect"). For each screen:
> - Screenshot at desktop width; then resize to a phone width (375px, e.g. the `mobile` preset), reload, and screenshot again. Reset to desktop when done.
> - Tab through the main flow with the keyboard: is focus visible and in order? Hover the main controls.
> - Read the text (e.g. `get_page_text`): copy, consistency of terms, capitalization.
> - Trigger the states you can safely reach (empty input, invalid input, long input such as a 120-character name, opening confirms).
> - Compare with the neighbouring screens: same components, spacing, colours and patterns for the same job?
>
> Don't change the UI language; it may be shared with other tabs.
>
> Report in two parts. First, an overall impression (3 sentences), 2–3 genuine strengths, and the squint-test result. Then findings, most important first. Each finding has: severity P0–P3, checklist item number(s), screen + state, what you saw (quote the text or describe the screenshot precisely), why it matters, and one concrete fix in the project's own terms (which token, class or component to use). Every finding needs evidence you actually observed. Mark anything you inferred without seeing it as "unverified".

### B. Code pass (you)
While the live review runs:
1. Run the drift scan on the scope, and once on the whole frontend for a baseline:
   ```bash
   python3 -I ~/.claude/skills/check-design/scripts/scan_design.py <scope paths>
   python3 -I ~/.claude/skills/check-design/scripts/scan_design.py --summary <frontend source dir>
   ```
   It picks up the profile's `design-scan.json` by itself (or pass `--config`). Without one it finds the palette in the theme config and global CSS and runs the generic rules; the last lines say what it used. If the project's design system isn't Tailwind or CSS-variable based, the colour and scale rules may say little: rely on reading the code.
   The scan is evidence, not a verdict. Judge each hit. Raw hex that equals a token is P3 polish. Off-palette colours, off-scale sizes and re-declared components are real drift. Something the whole app does the same way is system-level debt: mention it once, don't pin it on this feature.
2. Read the scope's components for what the scan can't see:
   - states: loading, empty, error, disabled reasons
   - semantics: buttons vs divs, labels, `aria-*`, focus handling in dialogs
   - copy: if the app is translated, everything through the i18n function with keys in every locale; sentence case (or the project's own convention); verb + object buttons; no backend text leaking into the UI
   - motion
   - reuse of the project's shared components (modal, confirm, toast, pagination, card, button, badge)
   - native `window.confirm`/`prompt`/`alert`
3. Note contrast risks from the actual colour pairs used (compute the ratio; e.g. a muted grey around 3.4:1 on white is too low for body text).

### C. Language pass (you, after A finishes; only if the app has more than one locale)
Switch the UI to the locale most users use, or the one with the longest strings if that isn't English, and revisit the screens with page text plus a screenshot or two. Run the project's i18n check script if there is one. Look for:
- raw keys
- untranslated text or backend text in the source language
- truncation and wrapping problems
- buttons that grow out of their layout

Switch back to the language you found. Do this only when no other agent is using the browser, because the language setting is often shared across tabs.

## 3. Synthesize
1. **Merge and dedupe** the live findings with your code findings. A problem seen both live and in code is strong. Something two passes found independently is likely real.
2. **Evidence gate (ibelick's rule).** Keep a finding only if it has all three:
   - a rule: a checklist item, a token or component in the design system, or a direct inconsistency between two screens
   - evidence that it actually happens on this surface: a screenshot description, quoted text or `file:line`
   - one concrete fix
   Drop anything that is only taste.
3. **Falsify.** Re-open the source or screen for each surviving finding and try to prove it wrong. Look for counter-evidence, an intentional system decision (see the design notes) or a misread state. Drop or downgrade what doesn't survive.
4. **Score** each dimension 0–4 (0 = broken, 2 = acceptable, 4 = excellent), with one line of reasoning each:
   - **System fidelity:** tokens, components, matches neighbours
   - **Hierarchy & layout:** squint test, primary action, spacing, grouping
   - **States & feedback:** loading, empty, error, success, disabled reasons
   - **Forms & copy:** labels, validation, wording, capitalization, every locale
   - **Accessibility:** contrast, keyboard, focus, semantics, names
   - **Responsive & robustness:** 375px, zoom, long content, longer translations

   Total /24. Bands: 21–24 excellent · 16–20 good · 11–15 needs work · ≤10 poor. Most real screens land at 12–19; don't inflate.

## 4. Report
Write to the profile's report folder, or by default `~/.claude/reports/<repo>/design-review/`, as `<surface-slug>-<YYYY-MM-DD>.md`. Then give the user a short summary in chat with the path.

```markdown
# Design review: <surface>, <date>

## Verdict
<one or two sentences: how consistent, coherent and good it is, and the single most important thing to fix>
**Score:** <n>/24 (<band>): fidelity x · hierarchy x · states x · forms & copy x · a11y x · responsive x

## What works
- <2–3 genuine strengths>

## Fix first
| # | Sev | Problem | Where (screen/state or file:line) | Evidence | Fix (in the project's terms) |
<P0–P2 only, at most ~10, most important first>

## Design-system drift
| Rule | In this surface | App baseline | Note |
<from the scan: e.g. off-palette #13D6B0 ×4 (app ×221). "Also app-wide" vs "new in this feature">

## Other languages
<raw keys, untranslated text, overflow; "no issues in <locale>"; or "single-language app">

## Polish (P3)
- <short list, one line each; keep it short>

## Questions for you
- <1–3 decisions the review can't make: product intent, scope, trade-offs>
```

Don't pad the report: an empty section reads "none". Offer to fix the top findings as a follow-up. For code fixes, refine-code's behavior-preserving loop applies.

**No profile or design notes yet?** Offer to save what you learned in step 0 as `~/.claude/project-profiles/<repo>/profile.md` and `design-system.md` (template in the README there), so the next review starts from it. Write only what you verified.
