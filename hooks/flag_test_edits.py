#!/usr/bin/env python3
"""PostToolUse (Edit, Write, MultiEdit): warn the agent when an edit weakens a test."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import hookio, repo, test_edits  # noqa: E402


def _before_and_after(data: hookio.HookInput, path: Path) -> tuple[str, str] | None:
    tool = hookio.text(data, "tool_name")
    args = hookio.tool_input(data)
    if tool == "Edit":
        return hookio.text(args, "old_string"), hookio.text(args, "new_string")
    if tool == "MultiEdit":
        edits = args.get("edits")
        items = cast(list[dict[str, object]], edits) if isinstance(edits, list) else []
        old = "\n".join(hookio.text(e, "old_string") for e in items if isinstance(e, dict))
        new = "\n".join(hookio.text(e, "new_string") for e in items if isinstance(e, dict))
        return old, new
    if tool == "Write":
        root = repo.find_repo_root(path.parent)
        if root is None:
            return None
        committed = repo.file_at_head(root, path.resolve().relative_to(root.resolve()).as_posix())
        return None if committed is None else (committed, hookio.text(args, "content"))
    return None


def handle(data: hookio.HookInput) -> None:
    file_path = hookio.text(hookio.tool_input(data), "file_path")
    if not file_path or not test_edits.is_test_file(file_path):
        return
    texts = _before_and_after(data, Path(file_path))
    if texts is None:
        return
    finding = test_edits.compare(*texts)
    if finding.weakens:
        hookio.block(test_edits.warning(file_path, finding))


if __name__ == "__main__":
    hookio.run("flag-test-edits", handle)
