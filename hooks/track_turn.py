#!/usr/bin/env python3
"""UserPromptSubmit: remember the working tree's state when the turn starts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import hookio, repo, state  # noqa: E402


def handle(data: hookio.HookInput) -> None:
    root = repo.find_repo_root(hookio.cwd(data))
    if root is None:
        return
    state.record_turn_start(root, hookio.text(data, "session_id"), repo.tree_hash(root))


if __name__ == "__main__":
    hookio.run("track-turn", handle)
