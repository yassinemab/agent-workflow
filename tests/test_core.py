from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aw.checks_gate import TurnState, block_reason
from aw.config import EMPTY_CONFIG, Check, ConfigError, WorkflowConfig, parse_config
from aw.globs import matches
from aw.state import CheckRecord
from aw.test_edits import compare, is_test_file

SOURCE = Path("workflow.json")
CONFIG = WorkflowConfig(
    source=SOURCE,
    checks=(Check("tests", ".", "true"),),
    no_checks_needed_for=("*.md", "**/*.md", "docs/**"),
    blocked_commands=(),
)


def turn(changed: tuple[str, ...], *, active: bool = False, start: str | None = "t0") -> TurnState:
    return TurnState(
        turn_start_tree=start, current_tree="t1", changed_paths=changed, stop_hook_active=active
    )


def record(trees: tuple[str, ...], passed: bool, failed: tuple[str, ...] = ()) -> CheckRecord:
    return CheckRecord(trees=trees, passed=passed, failed=failed, finished_at=0.0)


class Globs(unittest.TestCase):
    def test_single_star_stays_in_one_segment(self) -> None:
        self.assertTrue(matches("README.md", "*.md"))
        self.assertFalse(matches("docs/a.md", "*.md"))

    def test_double_star_crosses_segments(self) -> None:
        self.assertTrue(matches("docs/a.md", "**/*.md"))
        self.assertTrue(matches("a.md", "**/*.md"))
        self.assertTrue(matches("docs/adr/0001-x.md", "docs/**"))
        self.assertFalse(matches("src/docs.py", "docs/**"))

    def test_question_mark_and_literal_dots(self) -> None:
        self.assertTrue(matches("a1.py", "a?.py"))
        self.assertFalse(matches("a1xpy", "a?.py"))


class ParsingWorkflowJson(unittest.TestCase):
    def test_full_config(self) -> None:
        config = parse_config(
            {
                "checks": [{"name": "unit", "cwd": "backend", "run": "pytest"}],
                "no_checks_needed_for": ["*.csv"],
                "blocked_commands": [{"pattern": "mysqldump", "reason": "locks"}],
            },
            SOURCE,
        )
        self.assertEqual(config.checks, (Check("unit", "backend", "pytest"),))
        self.assertEqual(config.no_checks_needed_for, ("*.csv",))
        self.assertEqual(config.blocked_commands[0].reason, "locks")

    def test_defaults(self) -> None:
        config = parse_config({"checks": [{"name": "unit", "run": "pytest"}]}, SOURCE)
        self.assertEqual(config.checks[0].cwd, ".")
        self.assertEqual(config.checks[0].timeout_minutes, 20)
        self.assertEqual(config.no_checks_needed_for, EMPTY_CONFIG.no_checks_needed_for)

    def test_invalid_configs_fail_loudly(self) -> None:
        for raw in (
            [],
            {"check": []},
            {"checks": {}},
            {"checks": [{"name": "unit"}]},
            {"blocked_commands": [{"pattern": "(", "reason": "x"}]},
            {"checks": [{"name": "unit", "run": "x", "timeout_minutes": 0}]},
            {"checks": [{"name": "unit", "run": "x", "timeout_minutes": "5"}]},
            {"checks": [{"name": "unit", "run": "x", "timeout_minutes": -1}]},
        ):
            with self.assertRaises(ConfigError, msg=json.dumps(raw)):
                parse_config(raw, SOURCE)


class EndingATurn(unittest.TestCase):
    def test_allowed_when_nothing_changed_or_no_baseline(self) -> None:
        unchanged = TurnState("t1", "t1", (), False)
        self.assertIsNone(block_reason(unchanged, CONFIG, None))
        self.assertIsNone(block_reason(turn(("app.py",), start=None), CONFIG, None))

    def test_allowed_when_only_docs_changed(self) -> None:
        self.assertIsNone(block_reason(turn(("README.md", "docs/adr/0001-x.md")), CONFIG, None))

    def test_blocked_when_code_changed_and_checks_never_ran_on_it(self) -> None:
        reason = block_reason(turn(("app.py", "README.md")), CONFIG, record(("t0",), True))
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("1 file: app.py", reason)
        self.assertIn("run-checks", reason)

    def test_still_blocked_on_a_second_stop_without_a_run(self) -> None:
        self.assertIsNotNone(block_reason(turn(("app.py",), active=True), CONFIG, None))

    def test_allowed_when_checks_passed_on_the_current_state(self) -> None:
        self.assertIsNone(block_reason(turn(("app.py",)), CONFIG, record(("t1",), True)))
        self.assertIsNone(block_reason(turn(("app.py",)), CONFIG, record(("t0", "t1"), True)))

    def test_failed_checks_block_once_so_the_agent_reports_them(self) -> None:
        failing = record(("t1",), False, ("backend tests",))
        reason = block_reason(turn(("app.py",)), CONFIG, failing)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("backend tests", reason)
        self.assertIsNone(block_reason(turn(("app.py",), active=True), CONFIG, failing))

    def test_repo_without_checks_gets_one_reminder(self) -> None:
        self.assertIsNotNone(block_reason(turn(("app.py",)), EMPTY_CONFIG, None))
        self.assertIsNone(block_reason(turn(("app.py",), active=True), EMPTY_CONFIG, None))

    def test_long_path_lists_are_shortened(self) -> None:
        paths = tuple(f"src/m{i}.py" for i in range(7))
        reason = block_reason(turn(paths), CONFIG, None)
        assert reason is not None
        self.assertIn("7 files: src/m0.py, src/m1.py, src/m2.py, src/m3.py, src/m4.py and 2 more", reason)


class WeakenedTests(unittest.TestCase):
    def test_recognizes_test_files(self) -> None:
        for path in (
            "backend/app/tests/test_invoices.py",
            "app/tests.py",
            "pkg/invoice_test.py",
            "frontend/tests/unit/Invoice.test.tsx",
            "src/a.spec.ts",
            "src/__tests__/a.ts",
        ):
            self.assertTrue(is_test_file(path), path)
        for path in ("app/views/invoices.py", "src/testing_utils.ts", "contest.py"):
            self.assertFalse(is_test_file(path), path)

    def test_removed_assertions_are_counted(self) -> None:
        old = "self.assertEqual(a, 1)\nself.assertTrue(b)\nexpect(x).toBe(2)"
        new = "self.assertEqual(a, 1)"
        self.assertEqual(compare(old, new).removed_assertions, 2)

    def test_added_skips_are_counted(self) -> None:
        self.assertEqual(compare("def test_a():", "@unittest.skip('later')\ndef test_a():").added_skips, 1)
        self.assertEqual(compare("it('a', () => {", "it.skip('a', () => {").added_skips, 1)
        self.assertEqual(compare("test('a', f)", "xtest('a', f)").added_skips, 1)
        self.assertEqual(compare("", "@pytest.mark.xfail\n").added_skips, 1)

    def test_strengthening_a_test_is_not_flagged(self) -> None:
        finding = compare("self.assertTrue(x)", "self.assertTrue(x)\nself.assertEqual(y, 2)")
        self.assertFalse(finding.weakens)

    def test_changing_values_with_the_same_assertions_is_not_flagged(self) -> None:
        self.assertFalse(compare("assertEqual(total, 10)", "assertEqual(total, 12)").weakens)


if __name__ == "__main__":
    unittest.main()
