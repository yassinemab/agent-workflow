from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aw.checks_gate import RepoTurn, block_reason, checks_status, code_paths
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


def turn(changed: tuple[str, ...], checks: str = "missing", *, active: bool = False, failed: tuple[str, ...] = ()) -> RepoTurn:
    return RepoTurn(repo="/r", changed=changed, checks=checks, failed=failed, stop_hook_active=active)


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
    def test_allowed_when_this_session_changed_nothing(self) -> None:
        self.assertIsNone(block_reason(turn(()), CONFIG))

    def test_docs_need_no_checks(self) -> None:
        self.assertEqual(code_paths(("README.md", "docs/adr/0001-x.md", "app.py"), CONFIG), ("app.py",))
        self.assertEqual(code_paths(("README.md", "docs/adr/0001-x.md"), CONFIG), ())

    def test_blocked_when_code_changed_and_no_check_run_covers_it(self) -> None:
        reason = block_reason(turn(("app.py",)), CONFIG)
        assert reason is not None
        self.assertIn("in /r (1 file: app.py)", reason)
        self.assertIn("run-checks", reason)

    def test_still_blocked_on_a_second_stop_without_a_run(self) -> None:
        self.assertIsNotNone(block_reason(turn(("app.py",), active=True), CONFIG))

    def test_allowed_when_a_passing_run_covers_the_changes(self) -> None:
        self.assertIsNone(block_reason(turn(("app.py",), "passed"), CONFIG))

    def test_failed_checks_block_once_so_the_agent_reports_them(self) -> None:
        reason = block_reason(turn(("app.py",), "failed", failed=("backend tests",)), CONFIG)
        assert reason is not None
        self.assertIn("failed for the current state of your changes: backend tests", reason)
        self.assertIsNone(block_reason(turn(("app.py",), "failed", active=True, failed=("x",)), CONFIG))

    def test_repo_without_checks_gets_one_reminder(self) -> None:
        self.assertIsNotNone(block_reason(turn(("app.py",)), EMPTY_CONFIG))
        self.assertIsNone(block_reason(turn(("app.py",), active=True), EMPTY_CONFIG))

    def test_long_path_lists_are_shortened(self) -> None:
        paths = tuple(f"src/m{i}.py" for i in range(7))
        reason = block_reason(turn(paths), CONFIG)
        assert reason is not None
        self.assertIn("7 files: src/m0.py, src/m1.py, src/m2.py, src/m3.py, src/m4.py and 2 more", reason)


class WhichRunCoversTheChanges(unittest.TestCase):
    def changed_between(self, differences: dict[str, set[str]]):
        return lambda tree: differences[tree]

    def test_no_record_means_missing(self) -> None:
        self.assertEqual(checks_status(None, ("app.py",), self.changed_between({})), ("missing", ()))

    def test_a_run_covers_the_changes_when_none_of_them_changed_since(self) -> None:
        # Someone else changed other.py after the run; this session's app.py is as it was checked.
        status = checks_status(record(("t1",), True), ("app.py",), self.changed_between({"t1": {"other.py"}}))
        self.assertEqual(status, ("passed", ()))

    def test_a_run_doesnt_cover_files_edited_after_it(self) -> None:
        status = checks_status(record(("t1",), True), ("app.py",), self.changed_between({"t1": {"app.py"}}))
        self.assertEqual(status, ("missing", ()))

    def test_any_recorded_tree_can_cover_and_failures_are_reported(self) -> None:
        trees = self.changed_between({"t0": {"app.py"}, "t1": set()})
        self.assertEqual(checks_status(record(("t0", "t1"), False, ("unit",)), ("app.py",), trees), ("failed", ("unit",)))


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
