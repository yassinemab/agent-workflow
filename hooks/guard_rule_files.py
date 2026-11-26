#!/usr/bin/env python3
"""PreToolUse (Edit, Write, MultiEdit, NotebookEdit, Bash): ask the user before the
agent workflow changes: anything in ~/agent-workflow (rules, skills, hooks),
~/.claude/CLAUDE.md, and ~/.claude/settings*.json, where the hooks are registered.

In normal permission modes this shows Claude Code's confirmation prompt. In
bypass-permissions mode Claude Code shows no prompts, so the rule in AGENTS.md
section 11 applies on its own: change the workflow only after the user's
explicit yes in chat.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import hookio, writes  # noqa: E402

HOME = Path(os.environ.get("AW_USER_HOME", str(Path.home())))
# The links in ~/.codex, ~/.agents and ~/.claude resolve into ~/agent-workflow.
PROTECTED_PATHS = (
    HOME / "agent-workflow",
    HOME / ".claude" / "CLAUDE.md",
    HOME / ".claude" / "settings.json",
    HOME / ".claude" / "settings.local.json",
)
# How the protected files show up in shell commands.
PROTECTED_NAMES = (
    "agent-workflow",
    ".codex/AGENTS.md",
    *(f"{home}/.claude/{name}" for home in ("~", "$HOME", str(HOME)) for name in ("CLAUDE.md", "settings")),
)
ASK_REASON = (
    "This changes the agent workflow (rules, skills, hooks or their settings). Only do this "
    "after the user explicitly said yes in chat to this exact change (AGENTS.md section 11)."
)


def touches_protected(tool: str, args: dict[str, object]) -> bool:
    if tool == "Bash":
        return writes.command_writes_protected(hookio.text(args, "command"), PROTECTED_NAMES)
    target = hookio.text(args, "file_path") or hookio.text(args, "notebook_path")
    return bool(target) and any(writes.is_protected(Path(target), path) for path in PROTECTED_PATHS)


def handle(data: hookio.HookInput) -> None:
    if hookio.text(data, "permission_mode") == "bypassPermissions":
        return
    if touches_protected(hookio.text(data, "tool_name"), hookio.tool_input(data)):
        hookio.pre_tool_use("ask", ASK_REASON)


if __name__ == "__main__":
    hookio.run("guard-rule-files", handle, fail_closed=True)
