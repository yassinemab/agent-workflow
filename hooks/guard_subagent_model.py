#!/usr/bin/env python3
"""PreToolUse (Agent): keep subagents on a cheaper model than the main session."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import hookio, subagents  # noqa: E402


def handle(data: hookio.HookInput) -> None:
    verdict = subagents.check_subagent(hookio.tool_input(data))
    if not verdict.allowed:
        hookio.pre_tool_use("deny", verdict.reason)


if __name__ == "__main__":
    hookio.run("guard-subagent-model", handle, fail_closed=True)
