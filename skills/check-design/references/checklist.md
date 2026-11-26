# Design review checklist

Paraphrased and merged from six public skills (see "Sources" at the end). Tags: **F** frontend-design (Anthropic), **W** webapp-testing (Anthropic), **P** ui-ux-pro-max, **I** impeccable, **U** ui-skills (ibelick), **V** Vercel web-design-guidelines. Where they disagree, the project's design-system notes decide (see SKILL.md step 0); without them, the project's existing patterns decide.

Each item is something you can verify on the rendered page (R) or in the code (C).

## A. Consistency with the project's design system
1. Colours, radii, shadows, font sizes come from tokens / the scale; the scan script finds the exceptions. (C) [P I U]
2. Existing components are reused (card, button, badge, modal, confirm dialog, toast, pagination and skeleton components or classes the project already has). (C) [I U]
3. The same thing looks and behaves the same everywhere: if "Save" looks different on two screens, one is wrong. Compare with 1–2 neighbouring screens. (R) [I P]
4. One icon family (the one the project uses), consistent outline/solid per level, consistent size. No emoji as icons. (R/C) [P I]
5. One elevation per element: border *or* shadow, not a hairline plus a big soft shadow on everything. (R) [P I]
6. Same meaning, same colour: status colours match the rest of the app. (R) [I P]
7. The feature follows the patterns of comparable screens (how saving works, where actions live, how detail views open). (R) [I]

## B. Hierarchy and layout
8. Squint test: blur your eyes; the primary element, secondary elements and groups are still obvious. (R) [I]
9. One primary action per view or region; others secondary/ghost. (R) [P I]
10. ≤4 options at a decision point; 8+ is overload; extra actions go into a menu. (R) [I]
11. Tight spacing inside groups, more between groups; more space above a heading than below. Spacing on the 4/8 scale, not one value everywhere. (R/C) [I P]
12. No cards inside cards; group by proximity before adding boxes. (R) [I]
13. Repeated cards/columns hold genuinely equivalent content. (R) [I F]
14. Consistent max width; text never touches the container or viewport edge (≥16px). (R) [P I]
15. Popovers, dropdowns and tooltips aren't clipped by an `overflow-hidden` parent. (R) [I]
16. Sticky/fixed bars don't cover content or the focused element. (R) [P V]
17. Long names, emails, URLs, IDs and translated strings wrap or truncate cleanly; flex children holding text have `min-w-0`. (R/C) [V P I]
18. No nested scroll areas fighting the page scroll; no arbitrary z-index. (R/C) [P U]
19. The user never has to remember something from a previous screen to act here. (R) [I]
20. Visual structure carries meaning: numbering only for real sequences, dividers/labels only when they inform. (R) [F I]

## C. Typography
21. On the project's type scale, clear roles, headings visibly larger than body. (C/R) [I P]
22. Nothing under 11px; 11px only in dense data. (C) [P I]
23. Line length of prose ≤ ~75 characters; line-height ≥1.4 for body. (R) [P I F]
24. `tabular-nums` on amounts, counts, dates in tables and totals. (C) [P I U V]
25. Headings in order (no h1 → h3). (C) [P U V]
26. No ALL-CAPS passages; no accent on a single word in a heading. (R) [I F]
27. `…` not `...`; loading labels end with `…` ("Saving…"). (C) [V]

## D. Colour and contrast
28. Text ≥4.5:1, large text ≥3:1, icons/borders/focus rings ≥3:1, in every state. Light-grey "muted" text is the usual failure: around 3.4:1 on white is fine for large or placeholder text, not for body. (R) [P I U]
29. No grey text on coloured backgrounds; use a darker shade of that hue. (R) [I]
30. Colour is never the only signal: status, errors and deltas also have text or an icon. (R) [P I U]
31. Accent colours reserved for actions, selection and status; not sprinkled as decoration. (R) [I U]
32. Disabled looks different from read-only, and not by colour alone. (R) [U P]

## E. Components and states
33. Every interactive element has hover, focus-visible, active, disabled and (if async) loading states. (R/C) [I P V]
34. Focus is visible (the project's focus ring); never `outline-none` without a replacement. (R/C) [P V U]
35. Actions are `<button>`, navigation is `<a>`/`<Link>`; no clickable divs. (C) [U V P]
36. Icon-only buttons have `aria-label`; decorative icons are hidden from screen readers. (C) [all]
37. Modals only when inline won't do; when used: focus moves in, is trapped, Esc closes, focus returns. (R) [I U V]
38. Hover-only affordances (row actions, tooltips) have a keyboard/touch equivalent. (R) [U I P]

## F. Forms
39. Every field has a visible label; placeholders are only examples. (R) [P I U V]
40. Format rules and help are shown before submit, next to the field. (R) [I P]
41. Errors appear next to the field, say what's wrong and how to fix it, and are linked (`aria-describedby`/`aria-invalid`). (R/C) [P U V I]
42. Don't flag untouched fields; clear an error as soon as it's fixed. (R) [P]
43. A failed submit keeps everything the user typed. (R) [P I]
44. Submit: disabled only while in flight (with a pending label) or with a visible reason; never a mystery-disabled button; no double submit. (R) [V P U]
45. Inputs accept the formats users type in their locale (e.g. decimal commas `1.234,56`, spaces, currency signs). (R) [P]
46. Unsaved changes are protected (draft or warning) where losing them hurts. (R) [V P]

## G. Feedback: loading, empty, error, success
47. Every action gives visible feedback within ~100ms. (R) [P]
48. Loading inside content uses skeletons shaped like the content; no layout jump when data arrives. (R) [I U P V]
49. Empty states say what will appear and offer one clear next action; "no results" offers clearing filters; "no access" says why. (R) [I U P]
50. Errors say what failed, why (if known) and what to do; no raw codes, and no untranslated backend text in a translated UI; retry where it makes sense. (R) [I P F]
51. One failing widget doesn't blank the page. (R) [I]
52. Success is confirmed briefly (the project's toast or inline). (R) [P I]
53. Destructive actions: name the object and consequence, use the project's confirm dialog (or undo), danger styling, away from the primary action. (R) [I V U P]
54. Permission and read-only states explain themselves. (R) [I]

## H. Navigation and state
55. The current location is visible (active tab, title, step). (R) [P I]
56. Detail views, tabs and filters are reflected in the URL; Back goes where users expect; reload keeps their place. (R) [V P]
57. Links are real links (cmd/middle-click works). (C) [V]

## I. Motion
58. Motion only for feedback, state change or continuity; no decorative or page-load animation. (R) [I F P]
59. Routine UI motion ≤ ~250ms, overlays ≤ ~400ms, exits faster than entrances, ease-out, no bounce. (C) [I U P]
60. Animate transform/opacity, not width/height/top/left. (C) [P U V]
61. Bigger animations respect `prefers-reduced-motion`. (C) [all]

## J. Responsive and accessible
62. No horizontal page scroll at 375px; tables scroll in their own container or adapt. (R) [P I]
63. Layout survives 200% zoom. (R) [I P]
64. The main flow works keyboard-only in visual order. (R) [I U P]
65. Targets ≥24×24px (≥44px if the screen is used on mobile). (R) [P I]

## K. Copy
66. Sentence case everywhere; consistent terms for the same thing across the feature and the app. (R) [I U]
67. Buttons say what happens: verb + object ("Approve and send", not "Submit"/"OK"); the result uses the same word ("Approved"). (R) [F I V]
68. Plain language from the user's side; no internal jargon or code names (env vars, statuses like `AWAITING_SUBMISSION`). (R) [F I]
69. Each idea said once; no heading restated by an intro line. (R) [I]
70. If the app is translated: all text through the i18n function with keys in every locale; plurals via i18n; numbers and dates via `Intl` with the user's locale. (C) [I V]
71. No marketing buzzwords ("seamless", "supercharge", "empower"). (R) [I]

## L. AI-slop tells (flag only when they appear)
72. Gradient text, purple/cyan glow, radial spotlight backgrounds. [I U P F]
73. An eyebrow above every heading; 01/02/03 numbering on non-sequences; an icon tile above every card heading. [I F]
74. One-sided coloured stripe on rounded cards, decorative glassmorphism, decorative grid backgrounds. [I]
75. A grid of identical icon + heading + text cards as the default layout; the "big number + small label + gradient" hero metric. [I F]

## Severity
- **P0:** blocks the task or misleads about data/money. Fix now.
- **P1:** significant difficulty, WCAG AA failure, or clear design-system break on a main path. Fix before release. Tiebreaker: "would a user contact support?" → at least P1.
- **P2:** annoying, with a workaround; local drift.
- **P3:** polish. Keep P3s few in the report.

## Sources
Rules are paraphrased, not copied. Licences: frontend-design and webapp-testing (`anthropics/skills`, Apache-2.0 per their LICENSE.txt), `nextlevelbuilder/ui-ux-pro-max-skill` (MIT), `pbakaus/impeccable` (Apache-2.0), `ibelick/ui-skills` (MIT), `vercel-labs/agent-skills` web-design-guidelines (MIT). Review-process ideas borrowed: impeccable's separate unanchored assessments and P0–P3 severity, ibelick's evidence-before-finding rule, Vercel's terse `file:line` findings, webapp-testing's "wait for the page to settle, then inspect the rendered state".
