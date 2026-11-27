"""Running headless Claude Code sessions in throwaway copies of an eval fixture."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T")


def claude_bin() -> str:
    """The `claude` executable; tests point `AW_CLAUDE_BIN` at a fake."""
    return os.environ.get("AW_CLAUDE_BIN", "claude")


def fixture_copy(fixture: Path, tmp: Path, extra_files: tuple[tuple[str, str], ...] = ()) -> Path:
    """Copy the fixture into `tmp` as a fresh git repo with one commit, then write `extra_files`
    on top as uncommitted changes."""
    repo = tmp / "billing-app"
    shutil.copytree(fixture, repo)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"]):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=evals@example.com", "-c", "user.name=evals", "commit", "-qm", "fixture"],
        cwd=repo, check=True, capture_output=True,
    )
    for name, content in extra_files:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(content)
    return repo


@dataclass(frozen=True)
class SessionEnd(Generic[T]):
    value: T
    timed_out: bool
    seconds: float


def run_session(
    command: list[str],
    cwd: Path,
    timeout_s: float,
    consume: Callable[[Iterable[str]], T],
    stderr_path: Path | None = None,
) -> SessionEnd[T]:
    """Run a session and hand its output lines to `consume`.

    `consume` may stop reading early; the session is then terminated. A
    watchdog kills the session after `timeout_s`, and only then is the
    session reported as timed out. `seconds` counts from the session's start.
    """
    started = time.monotonic()
    killed = threading.Event()
    with stderr_path.open("w") if stderr_path else open(os.devnull, "w") as stderr:
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=stderr, text=True)
        assert process.stdout is not None

        def kill() -> None:
            killed.set()
            process.kill()

        watchdog = threading.Timer(timeout_s, kill)
        watchdog.start()
        try:
            value = consume(process.stdout)
        finally:
            watchdog.cancel()
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    return SessionEnd(value=value, timed_out=killed.is_set(), seconds=round(time.monotonic() - started, 1))
