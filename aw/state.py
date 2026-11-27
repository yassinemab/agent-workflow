"""Where the hooks and scripts keep their logs and eval results."""

from __future__ import annotations

import os
from pathlib import Path


def state_dir() -> Path:
    """The folder for logs and eval results (`AW_STATE_DIR` overrides it)."""
    base = os.environ.get("AW_STATE_DIR")
    return Path(base) if base else Path.home() / ".cache" / "agent-workflow"
