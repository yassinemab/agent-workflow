"""Decides whether a turn may end, given what changed and what the checks covered."""

from __future__ import annotations

from dataclasses import dataclass

from aw.config import WorkflowConfig
from aw.globs import matches_any
from aw.state import CheckRecord

RUN_CHECKS = "~/agent-workflow/bin/run-checks"
_SHOWN_PATHS = 5


@dataclass(frozen=True)
class TurnState:
    turn_start_tree: str | None
    current_tree: str
    changed_paths: tuple[str, ...]
    stop_hook_active: bool


def code_paths(changed: tuple[str, ...], config: WorkflowConfig) -> tuple[str, ...]:
    """The changed paths that need checks (everything not matched by `no_checks_needed_for`)."""
    return tuple(path for path in changed if not matches_any(path, config.no_checks_needed_for))


def block_reason(turn: TurnState, config: WorkflowConfig, record: CheckRecord | None) -> str | None:
    """Why the turn may not end yet, or None when it may.

    A failed check run blocks once, so the agent reports the failures; a
    missing run keeps blocking, because nothing has verified the change.
    Claude Code caps consecutive Stop-hook blocks, so this cannot loop forever.
    """
    if turn.turn_start_tree is None or turn.turn_start_tree == turn.current_tree:
        return None
    paths = code_paths(turn.changed_paths, config)
    if not paths:
        return None
    summary = _describe(paths)

    if not config.checks:
        if turn.stop_hook_active:
            return None
        return (
            f"Code changed this turn ({summary}) and this repo has no checks configured in a "
            "workflow.json. Run the project's tests as its profile or README describes, report "
            "the command and the result, and suggest a workflow.json to the user "
            "(format: ~/.claude/project-profiles/README.md)."
        )

    if record is not None and turn.current_tree in record.trees:
        if record.passed or turn.stop_hook_active:
            return None
        return (
            f"The checks failed on the current state: {', '.join(record.failed)}. Fix the failures "
            "your change caused. Failures listed as known in the project profile are baseline: "
            "say so in your report, with the test names."
        )

    return (
        f"Code changed this turn ({summary}) and the checks haven't run on the current state. "
        f"Run `{RUN_CHECKS}` and report the command and the result. If some of these changes "
        "came from someone else working in this checkout, say so, and run the checks anyway."
    )


def _describe(paths: tuple[str, ...]) -> str:
    shown = ", ".join(paths[:_SHOWN_PATHS])
    more = len(paths) - _SHOWN_PATHS
    count = f"{len(paths)} file{'s' if len(paths) != 1 else ''}"
    return f"{count}: {shown}{f' and {more} more' if more > 0 else ''}"
