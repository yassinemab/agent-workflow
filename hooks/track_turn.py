#!/usr/bin/env python3
"""UserPromptSubmit: a new turn starts, so forget the previous turn's edits."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aw import hookio, state  # noqa: E402


def handle(data: hookio.HookInput) -> None:
    state.start_turn(hookio.text(data, "session_id"))


if __name__ == "__main__":
    hookio.run("track-turn", handle)
