"""State the hooks share, stored per work tree inside its git directory.

- The tree hash at the start of each turn, per session (written by `track-turn`).
- The result of the last `run-checks` run (read by `require-checks`).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from aw.repo import git_dir

_SAFE_SESSION = re.compile(r"[^A-Za-z0-9_-]")


@dataclass(frozen=True)
class CheckRecord:
    """The working-tree states a check run covered, and whether every check passed."""

    trees: tuple[str, ...]
    passed: bool
    failed: tuple[str, ...]
    finished_at: float


def _state_dir(root: Path) -> Path:
    path = git_dir(root) / "agent-workflow"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _turn_file(root: Path, session_id: str) -> Path:
    safe = _SAFE_SESSION.sub("_", session_id) or "unknown"
    return _state_dir(root) / f"turn-{safe}.json"


def record_turn_start(root: Path, session_id: str, tree: str) -> None:
    _turn_file(root, session_id).write_text(json.dumps({"tree": tree, "at": time.time()}))


def read_turn_start(root: Path, session_id: str) -> str | None:
    path = _turn_file(root, session_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    tree = data.get("tree") if isinstance(data, dict) else None
    return tree if isinstance(tree, str) else None


def record_checks(root: Path, record: CheckRecord) -> None:
    (_state_dir(root) / "checks.json").write_text(json.dumps(asdict(record)))


def read_checks(root: Path) -> CheckRecord | None:
    path = _state_dir(root) / "checks.json"
    if not path.is_file():
        return None
    try:
        data = cast(dict[str, object], json.loads(path.read_text()))
        return CheckRecord(
            trees=tuple(cast(list[str], data["trees"])),
            passed=bool(data["passed"]),
            failed=tuple(cast(list[str], data["failed"])),
            finished_at=float(cast(float, data["finished_at"])),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
