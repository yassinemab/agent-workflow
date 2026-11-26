#!/usr/bin/env python3
"""Stop: don't let a turn end while code this session changed hasn't been checked.

Only files this session edited count (recorded by track-edits), in whichever
repos they're in. Other sessions' changes in a shared checkout don't block it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import checks_gate, config, hookio, repo, state  # noqa: E402


def _reason_for(root: Path, edits: state.RepoEdits, stop_hook_active: bool) -> str | None:
    current = repo.tree_hash(root)
    changed = set(repo.changed_paths(root, edits.baseline, current)) & set(edits.files)
    workflow = config.load_config(root)
    mine = checks_gate.code_paths(changed, workflow)
    if not mine:
        return None
    status, failed = checks_gate.checks_status(
        state.read_checks(root), mine, lambda tree: repo.changed_paths(root, tree, current)
    )
    turn = checks_gate.RepoTurn(str(root), mine, status, failed, stop_hook_active)
    return checks_gate.block_reason(turn, workflow)


def handle(data: hookio.HookInput) -> None:
    active = data.get("stop_hook_active") is True
    reasons = [
        reason
        for root, edits in state.turn_edits(hookio.text(data, "session_id")).items()
        if root.is_dir() and (reason := _reason_for(root, edits, active))
    ]
    if reasons:
        hookio.block("\n\n".join(reasons))


if __name__ == "__main__":
    hookio.run("require-checks", handle)
