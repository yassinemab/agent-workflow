#!/usr/bin/env python3
"""PreToolUse (Bash): deny destructive git commands and project-blocked commands."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import config, guards, hookio, repo  # noqa: E402


def handle(data: hookio.HookInput) -> None:
    command = hookio.text(hookio.tool_input(data), "command")
    if not command:
        return
    cwd = hookio.cwd(data)
    root = repo.find_repo_root(cwd)
    try:
        blocked = config.load_config(root).blocked_commands if root else ()
    except config.ConfigError as error:  # a broken project config must not lock the shell
        hookio.log_event("config-error", str(error))
        blocked = ()

    def branch_of(path: str | None) -> str | None:
        target = repo.find_repo_root(cwd / path if path else cwd)
        return repo.current_branch(target) if target else None

    verdict = guards.check_command(command, branch_of, blocked)
    if not verdict.allowed:
        hookio.pre_tool_use("deny", verdict.reason)


if __name__ == "__main__":
    hookio.run("guard-commands", handle, fail_closed=True)
