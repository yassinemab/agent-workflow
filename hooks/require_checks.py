#!/usr/bin/env python3
"""Stop: don't let a turn end with changed code that the checks haven't covered."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import checks_gate, config, hookio, repo, state  # noqa: E402


def handle(data: hookio.HookInput) -> None:
    root = repo.find_repo_root(hookio.cwd(data))
    if root is None:
        return
    start = state.read_turn_start(root, hookio.text(data, "session_id"))
    if start is None:
        return
    current = repo.tree_hash(root)
    turn = checks_gate.TurnState(
        turn_start_tree=start,
        current_tree=current,
        changed_paths=tuple(repo.changed_paths(root, start, current)),
        stop_hook_active=data.get("stop_hook_active") is True,
    )
    reason = checks_gate.block_reason(turn, config.load_config(root), state.read_checks(root))
    if reason:
        hookio.block(reason)


if __name__ == "__main__":
    hookio.run("require-checks", handle)
