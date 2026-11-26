"""Spots edits that weaken a test file: fewer assertions, or new skips."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

_TEST_DIR = re.compile(r"(?:^|/)(?:tests?|__tests__|spec|specs|e2e)/")
_TEST_FILE = re.compile(
    r"(?:^test_.*\.py|.*_test\.py|^tests\.py|.*\.(?:test|spec)\.[cm]?[jt]sx?|.*_spec\.rb|.*Test\.(?:java|kt))\Z"
)
_ASSERTION = re.compile(
    r"\bassert\w*\b"  # assert x, assertEqual(, self.assertTrue(, assert_called_once_with(
    r"|\bexpect\s*\("  # expect(x)
    r"|\.should\b"
    r"|\bpytest\.raises\b"
)
_SKIP = re.compile(
    r"@(?:unittest\.)?skip\w*"
    r"|@(?:unittest\.)?expectedFailure"
    r"|\bpytest\.mark\.(?:skip|skipif|xfail)\b"
    r"|\bpytest\.skip\("
    r"|\bself\.skipTest\("
    r"|\b(?:it|test|describe|context)\.(?:skip|todo|only)\b"
    r"|\b[xf](?:it|describe|test)\s*\("
)


@dataclass(frozen=True)
class TestEditFinding:
    removed_assertions: int
    added_skips: int

    @property
    def weakens(self) -> bool:
        return self.removed_assertions > 0 or self.added_skips > 0


def is_test_file(path: str) -> bool:
    posix = PurePosixPath(path.replace("\\", "/"))
    return bool(_TEST_DIR.search(str(posix)) or _TEST_FILE.match(posix.name))


def compare(old: str, new: str) -> TestEditFinding:
    """Compare a test file's text (or an edited fragment of it) before and after."""
    return TestEditFinding(
        removed_assertions=max(0, len(_ASSERTION.findall(old)) - len(_ASSERTION.findall(new))),
        added_skips=max(0, len(_SKIP.findall(new)) - len(_SKIP.findall(old))),
    )


def warning(path: str, finding: TestEditFinding) -> str:
    parts: list[str] = []
    if finding.removed_assertions:
        parts.append(f"removed {finding.removed_assertions} assertion(s)")
    if finding.added_skips:
        parts.append(f"added {finding.added_skips} skip/only marker(s)")
    return (
        f"flag-test-edits: this edit to {path} {' and '.join(parts)}. If you did this to make a "
        "failing test pass, revert it and fix the code instead (AGENTS.md section 4). It's only "
        "allowed when the agreed behavior changed or the assertion moved elsewhere; then say "
        "which in your report."
    )
