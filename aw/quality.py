"""Quality evals: score runs with and without the workflow, and summarize their spread.

Scoring and reporting are pure functions; besides loading tasks.json, `bin/run-quality-evals`
does the I/O.
"""

from __future__ import annotations

import json
import re
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from aw.globs import matches_any

CATEGORIES = ("design", "readability", "fit")
ARMS = ("with", "without")
Scores = dict[str, int]
JudgeVerdict = dict[str, Scores]


class TaskError(ValueError):
    """tasks.json is invalid."""


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    allowed: tuple[str, ...]
    """Glob patterns for the files the agent may change."""
    spec: str | None = None
    """A spec file in the fixture that the judge also gets, if the task has one."""


@dataclass(frozen=True)
class RunScore:
    task: str
    arm: str
    index: int
    tests_passed: int
    tests_total: int
    flags: tuple[str, ...]
    judge: Scores | None
    judge_error: bool
    minutes: float
    cost_usd: float | None
    refused: int = 0
    """Tool calls the permission allowlist refused during the session."""

    @property
    def test_score(self) -> float:
        return self.tests_passed / self.tests_total if self.tests_total else 0.0


@dataclass(frozen=True)
class ArmSummary:
    runs: int
    mean_test: float
    stdev_test: float
    worst_test: float
    bad_rate: float
    judge_means: dict[str, float | None]
    mean_minutes: float
    mean_cost: float | None
    mean_refused: float


def load_tasks(path: Path) -> list[Task]:
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise TaskError(f"{path}: expected a list of tasks")
    tasks: list[Task] = []
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise TaskError(f"{path}: every task must be an object")
        data = cast(dict[str, object], item)
        task_id, prompt, allowed, spec = data.get("id"), data.get("prompt"), data.get("allowed"), data.get("spec")
        if not isinstance(task_id, str) or not task_id or any(t.id == task_id for t in tasks):
            raise TaskError(f"{path}: missing or duplicate id {task_id!r}")
        if not isinstance(prompt, str) or not prompt:
            raise TaskError(f"{path}: task {task_id} needs a prompt")
        if not isinstance(allowed, list) or not allowed or not all(isinstance(a, str) for a in allowed):
            raise TaskError(f"{path}: task {task_id} needs `allowed`, a non-empty list of path globs")
        if spec is not None and not isinstance(spec, str):
            raise TaskError(f"{path}: task {task_id}: `spec` must be a path")
        tasks.append(Task(task_id, prompt, tuple(cast(list[str], allowed)), spec))
    return tasks


def red_flags(changed: Iterable[str], allowed: tuple[str, ...], *, weakened: bool, incomplete: bool) -> tuple[str, ...]:
    flags: list[str] = []
    if weakened:
        flags.append("weakened-test")
    if any(not matches_any(path, allowed) for path in changed):
        flags.append("out-of-scope")
    if incomplete:
        flags.append("incomplete")
    return tuple(flags)


def is_bad(run: RunScore) -> bool:
    """Bad: a hidden test fails (or none ran), any red flag, or the judge rated it worse in 2+ categories."""
    if run.tests_total == 0 or run.tests_passed < run.tests_total or run.flags:
        return True
    return run.judge is not None and sum(1 for c in CATEGORIES if run.judge[c] == 1) >= 2


# --- Judge -------------------------------------------------------------------------------

_JUDGE_INSTRUCTIONS = """You compare two independent solutions, A and B, to the same programming task in the same small Python repository. Judge only the code and tests in the diffs below.

Score each solution in three categories, relative to the other solution:
- design: simple and cohesive, no needless layers, abstractions or options
- readability: clear names, easy to follow, no noise
- fit: does what the task asks, no more and no less; tests that prove the change are part of what was asked

Use 1 = worse than the other solution, 2 = about the same, 3 = better. If both are equally good or equally bad in a category, give both 2. Correctness is checked separately by tests; don't guess it.

Reply with JSON only, in exactly this shape:
{"A": {"design": 1, "readability": 1, "fit": 1, "why": "one sentence citing file:line"}, "B": {"design": 1, "readability": 1, "fit": 1, "why": "one sentence citing file:line"}}"""


def judge_prompt(task_prompt: str, spec_text: str | None, diff_a: str, diff_b: str) -> str:
    spec = f"\n\nThe spec the task refers to:\n{spec_text}" if spec_text else ""
    return (
        f"{_JUDGE_INSTRUCTIONS}\n\nThe task:\n{task_prompt}{spec}"
        f"\n\n=== A ===\n{diff_a or '(no changes)'}\n\n=== B ===\n{diff_b or '(no changes)'}\n"
    )


_FENCE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.S)


def parse_judge(reply: str) -> JudgeVerdict | None:
    """The judge's verdict, or None unless the reply is exactly the required JSON."""
    text = reply.strip()
    fenced = _FENCE.match(text)
    try:
        data = json.loads(fenced.group(1) if fenced else text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or set(data) != {"A", "B"}:
        return None
    verdict: JudgeVerdict = {}
    for label in ("A", "B"):
        scores = data[label]
        if not isinstance(scores, dict):
            return None
        values = [scores.get(c) for c in CATEGORIES]
        if not all(type(v) is int and 1 <= v <= 3 for v in values):
            return None
        verdict[label] = {c: cast(int, v) for c, v in zip(CATEGORIES, values)}
    return verdict


def resolve_judge(with_first: JudgeVerdict, without_first: JudgeVerdict) -> tuple[Scores, Scores]:
    """Combine the two order-swapped calls into (with-arm scores, without-arm scores).

    `with_first` showed the with arm as A; `without_first` showed it as B. A
    category where the two calls disagree becomes a tie (2 for both).
    """
    with_scores: Scores = {}
    without_scores: Scores = {}
    for category in CATEGORIES:
        agree = (
            with_first["A"][category] == without_first["B"][category]
            and with_first["B"][category] == without_first["A"][category]
        )
        with_scores[category] = with_first["A"][category] if agree else 2
        without_scores[category] = with_first["B"][category] if agree else 2
    return with_scores, without_scores


# --- Summary -----------------------------------------------------------------------------


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(runs: Iterable[RunScore]) -> dict[tuple[str, str], ArmSummary]:
    groups: dict[tuple[str, str], list[RunScore]] = {}
    for run in runs:
        groups.setdefault((run.task, run.arm), []).append(run)
    summary: dict[tuple[str, str], ArmSummary] = {}
    for key, group in groups.items():
        scores = [r.test_score for r in group]
        judged = [r.judge for r in group if r.judge is not None]
        summary[key] = ArmSummary(
            runs=len(group),
            mean_test=sum(scores) / len(scores),
            stdev_test=statistics.stdev(scores) if len(scores) > 1 else 0.0,
            worst_test=min(scores),
            bad_rate=sum(is_bad(r) for r in group) / len(group),
            judge_means={c: _mean([float(j[c]) for j in judged]) for c in CATEGORIES},
            mean_minutes=sum(r.minutes for r in group) / len(group),
            mean_cost=_mean([r.cost_usd for r in group if r.cost_usd is not None]),
            mean_refused=sum(r.refused for r in group) / len(group),
        )
    return summary


def _num(value: float | None, width: int, digits: int = 2) -> str:
    return f"{value:>{width}.{digits}f}" if value is not None else f"{'-':>{width}}"


def format_report(summary: dict[tuple[str, str], ArmSummary], judge_errors: int = 0) -> str:
    lines: list[str] = []
    for task in dict.fromkeys(task for task, _ in summary):
        lines.append(task)
        lines.append(f"{'arm':<8}{'runs':>5}{'tests':>7}{'spread':>8}{'worst':>7}{'bad':>6}{'design':>9}{'read':>7}{'fit':>6}{'min':>7}{'cost':>7}{'refused':>9}")
        for arm in ARMS:
            s = summary.get((task, arm))
            if s is None:
                continue
            cost = f"${s.mean_cost:.2f}" if s.mean_cost is not None else "-"
            lines.append(
                f"{arm:<8}{s.runs:>5}{s.mean_test:>7.2f}{s.stdev_test:>8.2f}{s.worst_test:>7.2f}{s.bad_rate:>6.0%}"
                f"{_num(s.judge_means['design'], 9)}{_num(s.judge_means['readability'], 7)}{_num(s.judge_means['fit'], 6)}"
                f"{s.mean_minutes:>7.1f}{cost:>7}{s.mean_refused:>9.1f}"
            )
        lines.append("")
    lines.append(
        "tests = share of hidden tests passed; spread = its standard deviation; worst = the worst run; "
        "bad = share of bad runs; judge scores are relative (1 worse, 2 same, 3 better than the paired run); "
        "refused = commands the permission allowlist refused, per run."
    )
    if judge_errors:
        lines.append(f"{judge_errors} judge comparison{'s' if judge_errors != 1 else ''} failed and {'have' if judge_errors != 1 else 'has'} no judge score.")
    lines.append("A handful of runs per arm shows only rough spread: a difference of one or two runs is noise.")
    return "\n".join(lines) + "\n"
