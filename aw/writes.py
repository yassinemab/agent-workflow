"""Decides whether a file write or shell command changes a protected path.

Only writes count: a redirect into a protected path, or a writing command
(`tee`, `cp`, `mv`, `rm`, `sed -i`, …) whose destination is protected.
Reading a protected file, or writing elsewhere in a command that also
mentions one, is fine.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from aw.guards import shell_c_argument, split_segments, strip_prefixes

_REDIRECTS = frozenset({">", ">>", ">|", "&>", "&>>"})
# Commands that change every path they're given.
_WRITE_ALL_ARGS = frozenset({"tee", "rm", "rmdir", "mv", "truncate", "touch", "chmod", "chown", "unlink"})
# Commands whose last path argument is the destination.
_WRITE_LAST_ARG = frozenset({"cp", "ln", "install", "rsync"})
_IN_PLACE_EDITORS = frozenset({"sed", "perl", "ruby"})
_INLINE_CODE = {"python": "-c", "python3": "-c", "node": "-e"}
_GIT_WRITES = frozenset({"checkout", "restore", "reset", "apply", "am", "stash", "mv", "rm"})


def is_protected(path: Path, protected: Path) -> bool:
    """Whether a path (after following links) is the protected path or inside it."""
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return False
    target = protected.expanduser().resolve()
    return resolved == target or target in resolved.parents


def command_writes_protected(command: str, protected_names: Sequence[str]) -> bool:
    """Whether a shell command writes to a path that mentions a protected name."""
    if not any(name in command for name in protected_names):
        return False
    return any(_segment_writes(tokens, protected_names) for tokens in split_segments(command))


def _mentions(text: str, names: Sequence[str]) -> bool:
    return any(name in text for name in names)


def _segment_writes(tokens: list[str], names: Sequence[str]) -> bool:
    for i, token in enumerate(tokens[:-1]):
        if token in _REDIRECTS and _mentions(tokens[i + 1], names):
            return True
    tokens = strip_prefixes(_without_redirects(tokens))
    if not tokens:
        return False
    inner = shell_c_argument(tokens)
    if inner is not None:
        return command_writes_protected(inner, names)
    program, args = Path(tokens[0]).name, tokens[1:]
    paths = [arg for arg in args if not arg.startswith("-")]
    if program in _WRITE_ALL_ARGS:
        return any(_mentions(path, names) for path in paths)
    if program in _WRITE_LAST_ARG:
        return bool(paths) and _mentions(paths[-1], names)
    if program == "dd":
        return any(arg.startswith("of=") and _mentions(arg, names) for arg in args)
    if program in _IN_PLACE_EDITORS:
        in_place = any(re.fullmatch(r"-[A-Za-z]*i[A-Za-z]*|--in-place(=.*)?|-i.*", arg) for arg in args)
        return in_place and any(_mentions(path, names) for path in paths)
    if program in _INLINE_CODE and _INLINE_CODE[program] in args:
        code_index = args.index(_INLINE_CODE[program]) + 1
        return code_index < len(args) and _mentions(args[code_index], names)
    if program == "git":
        return any(arg in _GIT_WRITES for arg in args) and _mentions(" ".join(args), names)
    return False


def _without_redirects(tokens: list[str]) -> list[str]:
    out: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
        elif token in _REDIRECTS or token in {"<", "<<", "<<<", ">&", "<&"}:
            skip = True
        else:
            out.append(token)
    return out
