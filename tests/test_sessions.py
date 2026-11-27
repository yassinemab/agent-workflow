from __future__ import annotations

import sys
import tempfile
import unittest
from collections.abc import Iterable
from pathlib import Path

from aw.sessions import run_session


def first_line(lines: Iterable[str]) -> str:
    for line in lines:
        return line.strip()
    return ""


def all_lines(lines: Iterable[str]) -> list[str]:
    return [line.strip() for line in lines]


def python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


class RunSession(unittest.TestCase):
    def test_a_normal_finish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            end = run_session(python("print('a'); print('b')"), Path(tmp), 10, all_lines)
        self.assertEqual((end.value, end.timed_out), (["a", "b"], False))

    def test_stopping_early_terminates_the_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            end = run_session(python("import time; print('a', flush=True); time.sleep(30)"), Path(tmp), 20, first_line)
        self.assertEqual((end.value, end.timed_out), ("a", False))
        self.assertLess(end.seconds, 15)

    def test_the_watchdog_kills_a_hung_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            end = run_session(python("import time; time.sleep(30)"), Path(tmp), 0.5, all_lines)
        self.assertTrue(end.timed_out)
        self.assertEqual(end.value, [])
        self.assertLess(end.seconds, 15)

    def test_stderr_is_saved_when_asked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "stderr.txt"
            run_session(python("import sys; sys.stderr.write('boom')"), Path(tmp), 10, all_lines, stderr_path=log)
            self.assertEqual(log.read_text(), "boom")


if __name__ == "__main__":
    unittest.main()
