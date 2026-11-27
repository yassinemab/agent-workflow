from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aw.config import Check, ConfigError, parse_config
from aw.globs import matches
from aw.test_edits import compare, is_test_file

SOURCE = Path("workflow.json")


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
                "blocked_commands": [{"pattern": "mysqldump", "reason": "locks"}],
            },
            SOURCE,
        )
        self.assertEqual(config.checks, (Check("unit", "backend", "pytest"),))
        self.assertEqual(config.blocked_commands[0].reason, "locks")

    def test_defaults(self) -> None:
        config = parse_config({"checks": [{"name": "unit", "run": "pytest"}]}, SOURCE)
        self.assertEqual(config.checks[0].cwd, ".")
        self.assertEqual(config.checks[0].timeout_minutes, 20)

    def test_the_retired_no_checks_needed_for_key_is_still_accepted(self) -> None:
        config = parse_config({"checks": [], "no_checks_needed_for": ["*.md"]}, SOURCE)
        self.assertEqual(config.checks, ())

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
