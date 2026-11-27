"""Read-only git queries the hooks and scripts need."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    """A git command failed."""


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def find_repo_root(cwd: Path) -> Path | None:
    """The top level of the git work tree containing `cwd`, or None outside git."""
    try:
        return Path(_git(["rev-parse", "--show-toplevel"], cwd))
    except (GitError, FileNotFoundError, NotADirectoryError):
        return None


def repo_name(root: Path) -> str:
    """The repository name from the origin remote, else the main checkout's folder name."""
    try:
        url = _git(["remote", "get-url", "origin"], root)
    except GitError:
        url = ""
    if url:
        name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        return name.removesuffix(".git")
    common = Path(_git(["rev-parse", "--path-format=absolute", "--git-common-dir"], root))
    return common.parent.name


def current_branch(root: Path) -> str | None:
    """The checked-out branch name, or None when HEAD is detached."""
    try:
        return _git(["symbolic-ref", "--quiet", "--short", "HEAD"], root) or None
    except GitError:
        return None


def file_at_head(root: Path, relative_path: str) -> str | None:
    """A file's committed content at HEAD, or None if it isn't tracked there."""
    try:
        return _git(["show", f"HEAD:{relative_path}"], root)
    except GitError:
        return None
