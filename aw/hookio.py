"""Reading Claude Code hook input, writing hook output, and logging hook decisions."""

from __future__ import annotations

import json
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import cast

from aw.state import state_dir

HookInput = dict[str, object]
_REASON_LIMIT = 300
_hook_name = "unknown"
_hook_cwd = ""


def events_path() -> Path:
    """Where hook decisions are logged, one JSON object per line (read by `retro`)."""
    return state_dir() / "events.jsonl"


def log_event(decision: str, reason: str) -> None:
    """Append one decision to the event log. Logging must never break a hook."""
    try:
        path = events_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "hook": _hook_name,
            "decision": decision,
            "cwd": _hook_cwd,
            "reason": reason[:_REASON_LIMIT],
        }
        with path.open("a") as log:
            log.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def read_input() -> HookInput:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("hook input must be a JSON object")
    return cast(HookInput, data)


def text(data: HookInput, key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def tool_input(data: HookInput) -> dict[str, object]:
    value = data.get("tool_input")
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def cwd(data: HookInput) -> Path:
    return Path(text(data, "cwd") or ".")


def emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload))


def pre_tool_use(decision: str, reason: str) -> None:
    log_event(decision, reason)
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }
    )


def block(reason: str) -> None:
    """Block a Stop, or feed a PostToolUse warning back to the agent."""
    log_event("block", reason)
    emit({"decision": "block", "reason": reason})


def run(name: str, handler: Callable[[HookInput], None], *, fail_closed: bool = False) -> None:
    """Run a hook.

    An unexpected error never wedges the session. A guard (`fail_closed=True`)
    denies the tool call, so a bug can't silently switch protection off; any
    other hook reports the error without blocking (exit 1).
    """
    global _hook_name, _hook_cwd
    _hook_name = name
    try:
        data = read_input()
        _hook_cwd = text(data, "cwd")
        handler(data)
    except Exception:
        details = traceback.format_exc()
        if fail_closed:
            pre_tool_use(
                "deny",
                f"The {name} guard crashed, so this call was blocked to stay safe. Tell the user "
                f"(the error is in {events_path()}); don't retry it in another form. "
                f"Error: {details.strip().splitlines()[-1]}",
            )
            log_event("crash", details)
            return
        log_event("crash", details)
        sys.stderr.write(f"agent-workflow hook {name} failed:\n{details}")
        sys.exit(1)
