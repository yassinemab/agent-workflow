---
name: fix-bug
description: Fix a bug at its root cause, proven by a test. First build a command that goes red on this exact bug, reproduce and minimize it, rank falsifiable hypotheses and confirm the cause with evidence. Then write the regression test, watch it fail, make the smallest fix, and run the tests of the touched modules. It looks for the same bug elsewhere, cleans up every debug line, never weakens a test, and reports the root cause with evidence. Use this whenever the user reports a bug, error, crash, regression, failing test, wrong number or "this doesn't work", or asks to debug, diagnose, investigate or fix something, even if they don't say "bug". Also when they only ask why something fails or "what's going on" with an error or a wrong result: that is a bug report, not just a question. Not for new behavior (use scope-feature) or for cleanups that change nothing visible (use refine-code).
---

# Fix bug

Find **why** it's broken, prove it, and fix the cause, not the symptom. A fix without a reproduction is a guess, and a guess that happens to pass is the most dangerous kind. Follow the global rules in `AGENTS.md`, especially §4 (tests) and §7 (scope).

Read the project profile first (how profiles work: `~/.claude/project-profiles/README.md`). It has the test commands, the known baseline failures and the rules for reading production data.

## Pick a lane

- **Small lane:** the cause is obvious and local (one function, one file), and the fix doesn't change a design. Do steps 1, 3, 4 and 6 only: a command that goes red on the bug, a regression test that fails first, the smallest fix, then the checks and a short report (cause, test, result). Skip the hypotheses, the wider search and the review.
- **Full lane:** everything else, or the moment the small lane's assumption breaks (the first fix doesn't hold, the cause is somewhere else, or it touches more than one or two files). Do every step.

Say which lane in one line.

## 1. Build a feedback loop that goes red

Before forming any theory, get **one command you have already run that fails on this exact bug**. That might be a test, a `curl`, a management-command call or a script against local data. Write down the command and its output.

- If the report is vague, pin it down first: the exact input, the exact wrong output, the expected output, and where it was seen (local, staging, production, which user or account).
- Production data or logs are read-only. Follow the project's rules exactly, for example never a full `mysqldump`.
- If you can't reproduce it, say so with what you tried, and ask the user for the missing detail. Don't fix what you can't see.

## 2. Minimize and hypothesize

1. Shrink the reproduction to the smallest input and the fewest steps that still fail.
2. Write **3–5 falsifiable hypotheses**, ranked by likelihood. For each, name the observation that would prove or kill it.
3. Test them in order, cheapest first, by reading code, adding temporary logging, or running variations. Tag every temporary debug line with one unique marker, such as `[DEBUG-a4f2]`, so they can be found and removed with a single search.
4. After two failed fix attempts, stop and question the premise: is the reproduction really this bug? Is the expected behavior really what the code was meant to do?

The root cause is confirmed when you can explain the full chain from input to wrong output, with `file:line`, and predict a variation's result before running it.

## 3. Regression test first

1. Write a test at the right seam (the public interface where the bug is visible) that encodes the **expected** behavior, named after it: `test_invoice_total_uses_decimal_comma_amounts`.
2. Run it and **watch it fail for the reason you found**.
3. If no seam lets you test this without mocking your own code, that's a finding: report it, and test at the nearest real seam.

## 4. Fix

- The smallest change that removes the cause. Typed (`AGENTS.md` §5). No refactors, renames or cleanups mixed in.
- If the real fix needs a design change (a new constraint, a different transaction boundary, a data migration), describe it to the user and agree on it before you make it. A significant change goes through `design-feature`.
- Run the regression test and watch it pass. Then run the tests of the modules you touched.

## 5. Widen and clean up

- **Same bug elsewhere:** search for the same pattern (the same helper misused, the same unguarded check-then-insert, the same parsing). Report each hit with `file:line`, and fix it only with the user's yes, as a separate change.
- **Data already affected:** if the bug wrote bad data, say how much (read-only query) and propose a repair. Never repair production data without an explicit request.
- **Clean up:** search for your debug marker and remove every hit. Remove scratch scripts you created.

## 6. Finish

1. Run the tests of every module you touched (the profile's single-module commands), not the full suite (`AGENTS.md` §4). Compare failures with the profile's known baseline. If you fixed a baseline failure, say so, so the profile can be updated.
2. Report following `AGENTS.md` §11:
   - **Root cause**, with `file:line` and the chain from input to wrong output.
   - **The reproduction command**: red before the fix, green after.
   - **The regression test**, and the targeted test result.
   - Other places with the same pattern, and any affected data.
   - The failure-pattern self-check, adjacent-code findings and rule proposals.
3. Offer `review-change` for a non-trivial fix. Don't commit or push unless the user asks.
