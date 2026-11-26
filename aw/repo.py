"""Read-only git queries the hooks and run-checks need."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


class GitError(RuntimeError):
    """A git command failed."""


def _git(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
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


def git_dir(root: Path) -> Path:
    """This work tree's own git directory (per worktree, not the shared one)."""
    return Path(_git(["rev-parse", "--absolute-git-dir"], root))


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


def tree_hash(root: Path) -> str:
    """A hash of the whole working tree: tracked and untracked files, minus ignored ones.

    It writes a git tree object from a fresh, temporary index, so the real
    index and the working tree are never touched. The index starts empty on
    purpose: a copy of the real one would trust its cached file timestamps
    and could miss an edit that keeps a file's size and timestamp.
    """
    with tempfile.TemporaryDirectory(prefix="aw-index-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        _git(["add", "--all", "--", "."], root, env)
        return _git(["write-tree"], root, env)


def changed_paths(root: Path, old_tree: str, new_tree: str) -> list[str]:
    """Repo-relative paths that differ between two tree hashes."""
    if old_tree == new_tree:
        return []
    output = _git(["diff", "--name-only", "--no-renames", old_tree, new_tree], root)
    return [line for line in output.splitlines() if line]


def file_at_head(root: Path, relative_path: str) -> str | None:
    """A file's committed content at HEAD, or None if it isn't tracked there."""
    try:
        return _git(["show", f"HEAD:{relative_path}"], root)
    except GitError:
        return None
