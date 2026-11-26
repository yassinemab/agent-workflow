"""Decides whether a turn may end, given what this session changed and what the checks covered."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from aw.config import WorkflowConfig
from aw.globs import matches_any
from aw.state import CheckRecord

RUN_CHECKS = "~/agent-workflow/bin/run-checks"
_SHOWN_PATHS = 5

CheckStatus = Literal["missing", "passed", "failed"]


@dataclass(frozen=True)
class RepoTurn:
    """One repo this session edited during the turn."""

    repo: str
    changed: tuple[str, ...]
    """Files this session edited that differ from the turn's baseline and need checks."""
    checks: CheckStatus
    """The latest run-checks result for the current content of those files."""
    failed: tuple[str, ...] = ()
    stop_hook_active: bool = False


def code_paths(changed: Iterable[str], config: WorkflowConfig) -> tuple[str, ...]:
    """The changed paths that need checks (everything not matched by `no_checks_needed_for`)."""
    return tuple(sorted(p for p in changed if not matches_any(p, config.no_checks_needed_for)))


def checks_status(
    record: CheckRecord | None, paths: tuple[str, ...], changed_since: Callable[[str], Iterable[str]]
) -> tuple[CheckStatus, tuple[str, ...]]:
    """Whether the last run covered these files as they are now.

    A run covers them when none of them changed between a tree it checked and
    now. Other people's edits after the run don't matter.
    """
    if record is None:
        return "missing", ()
    for tree in record.trees:
        if not set(paths) & set(changed_since(tree)):
            return ("passed", ()) if record.passed else ("failed", record.failed)
    return "missing", ()


def block_reason(turn: RepoTurn, config: WorkflowConfig) -> str | None:
    """Why the turn may not end yet, or None when it may.

    A failed run blocks once, so the agent reports the failures; a missing run
    keeps blocking, because nothing has verified the change. Claude Code caps
    consecutive Stop-hook blocks, so this cannot loop forever.
    """
    if not turn.changed or turn.checks == "passed":
        return None
    summary = f"in {turn.repo} ({_describe(turn.changed)})"

    if not config.checks:
        if turn.stop_hook_active:
            return None
        return (
            f"You changed code this turn {summary} and that repo has no checks configured in a "
            "workflow.json. Run the project's tests as its profile or README describes, report the "
            "command and the result, and suggest a workflow.json to the user "
            "(format: ~/.claude/project-profiles/README.md)."
        )

    if turn.checks == "failed":
        if turn.stop_hook_active:
            return None
        return (
            f"The checks failed for the current state of your changes: {', '.join(turn.failed)}. Fix "
            "the failures your change caused. Failures listed as known in the project profile are "
            "baseline: say so in your report, with the test names."
        )

    return (
        f"You changed code this turn {summary} and the checks haven't run on it as it is now. "
        f"Run `{RUN_CHECKS}` in that repo and report the command and the result."
    )


def _describe(paths: tuple[str, ...]) -> str:
    shown = ", ".join(paths[:_SHOWN_PATHS])
    more = len(paths) - _SHOWN_PATHS
    count = f"{len(paths)} file{'s' if len(paths) != 1 else ''}"
    return f"{count}: {shown}{f' and {more} more' if more > 0 else ''}"
