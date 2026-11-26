"""Grading for the workflow's evals: does a prompt reach the right skill, without
editing code first?

A case runs `claude -p` headless and is graded on the tool calls it makes, in
order, from the stream-json output. The run stops as soon as the verdict is
known, to keep evals cheap.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

NO_SKILL = "none"
EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})


class CaseError(ValueError):
    """cases.json is invalid."""


@dataclass(frozen=True)
class Case:
    id: str
    prompt: str
    expect_skills: tuple[str, ...]
    """Acceptable first skills, or ("none",) when no skill should run."""
    notes: str = ""
    uncommitted: tuple[tuple[str, str], ...] = ()
    """(path, content) pairs written into the fixture copy after its commit, e.g. a change to review."""

    @property
    def expects_no_skill(self) -> bool:
        return self.expect_skills == (NO_SKILL,)


@dataclass(frozen=True)
class ToolCall:
    name: str
    skill: str | None = None


@dataclass
class Observation:
    """What a run did so far."""

    calls: list[ToolCall] = field(default_factory=list)
    finished: bool = False
    cost_usd: float | None = None
    error: str | None = None
    final_text: str = ""


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reason: str


def load_cases(path: Path) -> list[Case]:
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise CaseError(f"{path}: expected a list of cases")
    cases: list[Case] = []
    seen: set[str] = set()
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise CaseError(f"{path}: every case must be an object")
        data = cast(dict[str, object], item)
        case_id, prompt, expect = data.get("id"), data.get("prompt"), data.get("expect_skill")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise CaseError(f"{path}: missing or duplicate id {case_id!r}")
        if not isinstance(prompt, str) or not prompt:
            raise CaseError(f"{path}: case {case_id} needs a prompt")
        if isinstance(expect, str):
            skills: tuple[str, ...] = (expect,)
        elif isinstance(expect, list) and expect and all(isinstance(s, str) for s in expect):
            skills = tuple(cast(list[str], expect))
        else:
            raise CaseError(f"{path}: case {case_id} needs expect_skill (a name, a list, or \"none\")")
        notes = data.get("notes", "")
        uncommitted = data.get("uncommitted", {})
        if not isinstance(uncommitted, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in cast(dict[object, object], uncommitted).items()
        ):
            raise CaseError(f"{path}: case {case_id}: `uncommitted` must map paths to file contents")
        files = tuple(sorted(cast(dict[str, str], uncommitted).items()))
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name, _ in files):
            raise CaseError(f"{path}: case {case_id}: `uncommitted` paths must stay inside the fixture")
        cases.append(Case(case_id, prompt, skills, notes if isinstance(notes, str) else "", files))
        seen.add(case_id)
    return cases


def tool_calls(event: dict[str, object]) -> list[ToolCall]:
    """The tool calls in one stream-json event (assistant messages only)."""
    if event.get("type") != "assistant":
        return []
    message = event.get("message")
    content = cast(dict[str, object], message).get("content") if isinstance(message, dict) else None
    calls: list[ToolCall] = []
    for block in cast(list[object], content) if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = str(block.get("name", ""))
            tool_input = block.get("input")
            skill = cast(dict[str, object], tool_input).get("skill") if isinstance(tool_input, dict) else None
            calls.append(ToolCall(name, str(skill) if name == "Skill" and skill else None))
    return calls


def observe(lines: Iterable[str], case: Case, max_calls: int) -> Observation:
    """Read stream-json lines until the verdict is known (see `decided`)."""
    seen = Observation()
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        data = cast(dict[str, object], event)
        seen.calls.extend(tool_calls(data))
        if data.get("type") == "result":
            seen.finished = True
            cost = data.get("total_cost_usd")
            seen.cost_usd = float(cost) if isinstance(cost, (int, float)) else None
            final = data.get("result")
            seen.final_text = final if isinstance(final, str) else ""
            if data.get("is_error") and data.get("subtype") != "error_max_budget_usd":
                seen.error = str(data.get("subtype"))
        if decided(seen, case, max_calls):
            break
    return seen


def decided(seen: Observation, case: Case, max_calls: int) -> bool:
    """Whether the run can stop: the verdict won't change with more output."""
    if seen.finished or len(seen.calls) >= max_calls:
        return True
    for call in seen.calls:
        if call.name == "Skill":
            return True
        if call.name in EDIT_TOOLS and not case.expects_no_skill:
            return True
    return False


def grade(seen: Observation, case: Case) -> Verdict:
    if seen.error:
        return Verdict(False, f"run failed: {seen.error}")
    first_skill: str | None = None
    for call in seen.calls:
        if call.name == "Skill":
            first_skill = call.skill
            break
        if call.name in EDIT_TOOLS and not case.expects_no_skill:
            return Verdict(False, f"tried {call.name} before loading a skill")

    if case.expects_no_skill:
        if first_skill is not None:
            return Verdict(False, f"used skill {first_skill}, expected none")
        return Verdict(True, "no skill, as expected")
    if first_skill is None:
        return Verdict(False, f"no skill within {len(seen.calls)} tool call(s)")
    if first_skill not in case.expect_skills:
        return Verdict(False, f"used {first_skill}, expected {' or '.join(case.expect_skills)}")
    return Verdict(True, f"used {first_skill}")
