"""State the hooks and scripts share.

- Per session (in the state folder): which files this session edited during
  the current turn, per repo, and each repo's tree hash before the first of
  those edits. Written by `track-turn` and `track-edits`, read by `require-checks`.
- Per work tree (in its git directory): the result of the last `run-checks` run.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from aw.repo import git_dir

_SAFE_SESSION = re.compile(r"[^A-Za-z0-9_-]")


def state_dir() -> Path:
    """The folder for logs, turn state and eval results (`AW_STATE_DIR` overrides it)."""
    base = os.environ.get("AW_STATE_DIR")
    return Path(base) if base else Path.home() / ".cache" / "agent-workflow"


@dataclass(frozen=True)
class CheckRecord:
    """The working-tree states a check run covered, and whether every check passed."""

    trees: tuple[str, ...]
    passed: bool
    failed: tuple[str, ...]
    finished_at: float


@dataclass(frozen=True)
class RepoEdits:
    """What this session edited in one repo during the current turn."""

    baseline: str
    files: tuple[str, ...]


# --- Per-session turn state ------------------------------------------------------


def _turn_file(session_id: str) -> Path:
    safe = _SAFE_SESSION.sub("_", session_id) or "unknown"
    path = state_dir() / "turns" / f"{safe}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _locked_turn(session_id: str) -> Iterator[dict[str, dict[str, object]]]:
    """The session's turn state, locked against hooks running in parallel, saved on exit."""
    path = _turn_file(session_id)
    with path.open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        try:
            data = json.loads(handle.read() or "{}")
        except json.JSONDecodeError:
            data = {}
        repos = cast(dict[str, dict[str, object]], data.get("repos", {}) if isinstance(data, dict) else {})
        yield repos
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({"repos": repos, "updated": time.time()}))


def start_turn(session_id: str) -> None:
    """Forget the previous turn's edits."""
    with _locked_turn(session_id) as repos:
        repos.clear()


def record_edit(session_id: str, root: Path, relative_path: str, baseline: Callable[[], str]) -> None:
    """Note that this session is about to edit a file; the first edit in a repo records its baseline."""
    with _locked_turn(session_id) as repos:
        entry = repos.setdefault(str(root), {"baseline": baseline(), "files": []})
        files = cast(list[str], entry["files"])
        if relative_path not in files:
            files.append(relative_path)


def turn_edits(session_id: str) -> dict[Path, RepoEdits]:
    with _locked_turn(session_id) as repos:
        return {
            Path(root): RepoEdits(
                baseline=str(entry["baseline"]), files=tuple(cast(list[str], entry["files"]))
            )
            for root, entry in repos.items()
        }


# --- Per-work-tree check results ---------------------------------------------------


def _checks_file(root: Path) -> Path:
    path = git_dir(root) / "agent-workflow" / "checks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_checks(root: Path, record: CheckRecord) -> None:
    _checks_file(root).write_text(json.dumps(asdict(record)))


def read_checks(root: Path) -> CheckRecord | None:
    path = _checks_file(root)
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
