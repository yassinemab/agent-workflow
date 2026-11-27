# 0002. A relative, blind judge whose verdict counts toward bad runs

- Status: Accepted
- Date: 2026-11-27
- Decided by: user (the scale and counting it right away), agent (blinding and order swap)

## Context
The quality evals measure the spread of results, so every run needs its own score. A pairwise judge ("A beats B") gives only a win rate. An absolute 1–5 grade turns into an ordinary LLM-as-judge with drifting standards.

## Decision
The judge sees run *i* of both arms of a task, labeled A and B without saying which arm is which. It also sees only the code and test diffs, so docs or ADRs the workflow adds can't give the arm away. It scores each run 1–3 per category (design, readability, fit to the request): 1 means worse than the other run, 2 about the same, 3 better. Each pair is judged twice with the order swapped, and a category where the two verdicts disagree gets 2 for both runs. A run the judge gives a 1 in at least 2 of the 3 categories counts as a bad run, from the first version on.

## Alternatives considered
- Pairwise win rate only: no per-run score, so no spread.
- Absolute 1–5 scores: less stable, and not what the user wanted.
- Report judge scores separately until they're validated against the user's own judgment: recommended by the agent, but the user chose to count them right away.

## Consequences
- The judge's scores aren't validated. A biased judge can make either arm look worse. Every judge reply is saved, so any verdict can be audited.
- Relative scores only make sense within a pair. They can't be compared across tasks or across eval runs.
- Before trusting the bad-run rate for decisions, compare the judge with your own verdicts on about 10 pairs.
