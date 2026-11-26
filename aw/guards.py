"""Decides which shell commands an agent may run without the user.

These are best-effort parsers over the command text. They catch the usual
forms of each dangerous command; they are a safety net under the rules in
AGENTS.md, not a sandbox.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from aw.config import BlockedCommand

PROTECTED_BRANCHES = frozenset({"main", "master"})
_OPERATORS = frozenset({"&&", "||", ";", "|", "&", "|&", ";;", "(", ")"})
_WRAPPERS = frozenset({"sudo", "command", "exec", "time", "nohup", "env", "nice"})
SHELLS = frozenset({"sh", "bash", "zsh", "dash"})
_GIT_OPTIONS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_ASK_USER = "If the user wants this, ask them to run it themselves."

BranchLookup = Callable[[str | None], str | None]
"""Returns the current branch for a `git -C` path (None means the hook's cwd)."""


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reason: str = ""


ALLOW = Verdict(allowed=True)


def check_command(
    command: str, branch_of: BranchLookup, blocked: Sequence[BlockedCommand] = ()
) -> Verdict:
    """Whether a shell command may run."""
    for rule in blocked:
        if rule.pattern.search(command):
            return Verdict(False, f"Blocked in this project: {rule.reason} {_ASK_USER}")
    for segment in split_segments(command):
        verdict = _check_segment(segment, branch_of, blocked)
        if not verdict.allowed:
            return verdict
    return ALLOW


def split_segments(command: str) -> list[list[str]]:
    """Split a command line into simple commands (on &&, ||, ;, | and newlines)."""
    lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes: fall back to a plain split
        tokens = command.replace("\n", " ; ").split()
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in _OPERATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def strip_prefixes(tokens: list[str]) -> list[str]:
    """Drop leading `VAR=value` assignments and wrappers like `sudo` or `env`."""
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token) or Path(token).name in _WRAPPERS:
            i += 1
        else:
            break
    return tokens[i:]


def shell_c_argument(tokens: list[str]) -> str | None:
    """The command string of `bash -c '<command>'`, or None."""
    if tokens and Path(tokens[0]).name in SHELLS and "-c" in tokens[1:-1]:
        return tokens[tokens.index("-c", 1) + 1]
    return None


def _check_segment(
    tokens: list[str], branch_of: BranchLookup, blocked: Sequence[BlockedCommand]
) -> Verdict:
    tokens = strip_prefixes(tokens)
    if not tokens:
        return ALLOW
    inner = shell_c_argument(tokens)
    if inner is not None:
        return check_command(inner, branch_of, blocked)
    if Path(tokens[0]).name != "git":
        return ALLOW
    repo_path, args = _git_global_options(tokens[1:])
    if not args:
        return ALLOW
    subcommand, rest = args[0], args[1:]
    checker = _GIT_CHECKS.get(subcommand)
    return checker(rest, lambda: branch_of(repo_path)) if checker else ALLOW


def _git_global_options(args: list[str]) -> tuple[str | None, list[str]]:
    """Skip git's global options; return the `-C` path (if any) and the rest."""
    repo_path: str | None = None
    i = 0
    while i < len(args) and args[i].startswith("-"):
        option = args[i]
        if option in _GIT_OPTIONS_WITH_VALUE and i + 1 < len(args):
            if option == "-C":
                repo_path = args[i + 1]
            i += 2
        else:
            i += 1
    return repo_path, args[i:]


def _has_short_flag(args: list[str], flag: str) -> bool:
    return any(re.fullmatch(rf"-[A-Za-z]*{flag}[A-Za-z]*", arg) for arg in args)


def _positionals(args: list[str]) -> list[str]:
    if "--" in args:
        before = args[: args.index("--")]
        return [arg for arg in before if not arg.startswith("-")]
    return [arg for arg in args if not arg.startswith("-")]


def _deny(what: str, why: str) -> Verdict:
    return Verdict(False, f"Blocked by guard-commands: `{what}` {why} {_ASK_USER}")


def _check_push(args: list[str], current_branch: Callable[[], str | None]) -> Verdict:
    if any(arg.startswith(("--force", "--mirror", "--delete")) for arg in args) or _has_short_flag(
        args, "[fd]"
    ):
        return _deny("git push --force/--delete/--mirror", "rewrites or deletes remote history.")
    if "--all" in args:
        return _deny("git push --all", "pushes every branch, including main.")
    refspecs = _positionals(args)[1:]
    if any(spec.startswith("+") for spec in refspecs):
        return _deny("git push +refspec", "is a force push.")
    if any(spec.startswith(":") for spec in refspecs):
        return _deny("git push :branch", "deletes a remote branch.")
    for spec in refspecs:
        destination = spec.split(":")[-1].removeprefix("refs/heads/")
        if destination == "HEAD":
            destination = current_branch() or ""
        if destination in PROTECTED_BRANCHES:
            return _deny(f"git push … {spec}", "pushes to a protected branch (it may deploy).")
    if not refspecs and current_branch() in PROTECTED_BRANCHES:
        return _deny("git push", "on main/master pushes to a protected branch (it may deploy).")
    return ALLOW


def _check_reset(args: list[str], _branch: Callable[[], str | None]) -> Verdict:
    if "--hard" in args:
        return _deny("git reset --hard", "throws away uncommitted work, possibly someone else's.")
    return ALLOW


def _check_stash(args: list[str], _branch: Callable[[], str | None]) -> Verdict:
    if args and args[0] in {"list", "show"}:
        return ALLOW
    return _deny("git stash", "moves uncommitted work, possibly another session's, out of the tree.")


def _check_checkout(args: list[str], _branch: Callable[[], str | None]) -> Verdict:
    if "--" in args or "." in args or "--force" in args or _has_short_flag(args, "f"):
        return _deny("git checkout -- <paths>", "overwrites uncommitted changes in those files.")
    return ALLOW


def _check_restore(args: list[str], _branch: Callable[[], str | None]) -> Verdict:
    staged_only = ("--staged" in args or _has_short_flag(args, "S")) and not (
        "--worktree" in args or _has_short_flag(args, "W")
    )
    if staged_only:
        return ALLOW
    return _deny("git restore", "overwrites uncommitted changes in those files.")


def _check_clean(args: list[str], _branch: Callable[[], str | None]) -> Verdict:
    dry_run = "--dry-run" in args or _has_short_flag(args, "n")
    if not dry_run and ("--force" in args or _has_short_flag(args, "f")):
        return _deny("git clean -f", "deletes untracked files for good.")
    return ALLOW


def _check_switch(args: list[str], _branch: Callable[[], str | None]) -> Verdict:
    if "--discard-changes" in args or "--force" in args or _has_short_flag(args, "f"):
        return _deny("git switch --discard-changes", "throws away uncommitted work.")
    return ALLOW


_GIT_CHECKS: dict[str, Callable[[list[str], Callable[[], str | None]], Verdict]] = {
    "push": _check_push,
    "reset": _check_reset,
    "stash": _check_stash,
    "checkout": _check_checkout,
    "restore": _check_restore,
    "clean": _check_clean,
    "switch": _check_switch,
}
