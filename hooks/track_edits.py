#!/usr/bin/env python3
"""PreToolUse (Edit, Write, MultiEdit, NotebookEdit): note which file this session is
about to edit, so require-checks only looks at this session's own changes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import hookio, repo, state  # noqa: E402


def _existing_dir(path: Path) -> Path:
    """The nearest folder that exists (a new file's folders may not exist yet)."""
    for candidate in (path.parent, *path.parents):
        if candidate.is_dir():
            return candidate
    return Path("/")


def handle(data: hookio.HookInput) -> None:
    args = hookio.tool_input(data)
    target = hookio.text(args, "file_path") or hookio.text(args, "notebook_path")
    if not target:
        return
    path = Path(target).expanduser()
    path = (hookio.cwd(data) / path if not path.is_absolute() else path).resolve()
    root = repo.find_repo_root(_existing_dir(path))
    if root is None:
        return
    root = root.resolve()
    state.record_edit(
        hookio.text(data, "session_id"),
        root,
        path.relative_to(root).as_posix(),
        lambda: repo.tree_hash(root),
    )


if __name__ == "__main__":
    hookio.run("track-edits", handle)
