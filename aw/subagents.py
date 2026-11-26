"""Subagents run on a cheaper model than the main session (AGENTS.md §1).

A subagent with no explicit model gets CLAUDE_CODE_SUBAGENT_MODEL (set to
sonnet by install.py) or its definition's model. What's left to stop is an
explicit request for an expensive model, and forks, which always run on the
main session's model.
"""

from __future__ import annotations

from dataclasses import dataclass

EXPENSIVE_MODELS = ("opus", "fable")
_ADVICE = (
    "Subagents run on a cheaper model than the main session (AGENTS.md section 1): use "
    "model \"sonnet\", or \"haiku\" for plain searching and reading."
)


@dataclass(frozen=True)
class SubagentVerdict:
    allowed: bool
    reason: str = ""


def check_subagent(tool_input: dict[str, object]) -> SubagentVerdict:
    if tool_input.get("subagent_type") == "fork":
        return SubagentVerdict(
            False,
            "Blocked by guard-subagent-model: a fork always runs on the main session's model. "
            f"Start a fresh subagent with a short brief instead. {_ADVICE}",
        )
    model = tool_input.get("model")
    if isinstance(model, str) and any(name in model.lower() for name in EXPENSIVE_MODELS):
        return SubagentVerdict(False, f"Blocked by guard-subagent-model: `{model}` is the expensive tier. {_ADVICE}")
    return SubagentVerdict(True)
