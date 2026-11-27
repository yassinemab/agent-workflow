from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aw.quality import (
    RunScore,
    TaskError,
    is_bad,
    judge_prompt,
    load_tasks,
    parse_judge,
    red_flags,
    resolve_judge,
    summarize,
    format_report,
)

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = ("billing/invoice.py", "tests/**")


def run(
    arm: str = "with",
    passed: int = 4,
    total: int = 4,
    flags: tuple[str, ...] = (),
    judge: dict[str, int] | None = None,
    minutes: float = 2.0,
    cost: float | None = 0.5,
    index: int = 1,
    refused: int = 0,
) -> RunScore:
    return RunScore(
        task="t", arm=arm, index=index, tests_passed=passed, tests_total=total, flags=flags,
        judge=judge, judge_error=False, minutes=minutes, cost_usd=cost, refused=refused,
    )


def verdict(a: tuple[int, int, int], b: tuple[int, int, int]) -> dict[str, dict[str, int]]:
    keys = ("design", "readability", "fit")
    return {"A": dict(zip(keys, a)), "B": dict(zip(keys, b))}


class RedFlags(unittest.TestCase):
    def test_no_flags_for_a_clean_run(self) -> None:
        self.assertEqual(red_flags(["billing/invoice.py", "tests/test_x.py"], ALLOWED, weakened=False, incomplete=False), ())

    def test_each_flag(self) -> None:
        self.assertEqual(red_flags(["billing/invoice.py"], ALLOWED, weakened=True, incomplete=False), ("weakened-test",))
        self.assertEqual(red_flags(["billing/reminders.py"], ALLOWED, weakened=False, incomplete=False), ("out-of-scope",))
        self.assertEqual(red_flags([], ALLOWED, weakened=False, incomplete=True), ("incomplete",))
        self.assertEqual(
            red_flags(["setup.py"], ALLOWED, weakened=True, incomplete=True), ("weakened-test", "out-of-scope", "incomplete")
        )


class BadRunRule(unittest.TestCase):
    def test_a_clean_passing_run_is_good(self) -> None:
        self.assertFalse(is_bad(run(judge={"design": 2, "readability": 1, "fit": 3})))

    def test_any_failing_hidden_test_makes_it_bad(self) -> None:
        self.assertTrue(is_bad(run(passed=3, total=4)))

    def test_any_red_flag_makes_it_bad(self) -> None:
        self.assertTrue(is_bad(run(flags=("out-of-scope",))))

    def test_the_judge_rating_it_worse_in_two_categories_makes_it_bad(self) -> None:
        self.assertTrue(is_bad(run(judge={"design": 1, "readability": 1, "fit": 3})))
        self.assertFalse(is_bad(run(judge={"design": 1, "readability": 2, "fit": 3})))

    def test_no_judge_score_doesnt_count_against_it(self) -> None:
        self.assertFalse(is_bad(run(judge=None)))

    def test_a_run_with_no_hidden_tests_counted_is_bad(self) -> None:
        self.assertTrue(is_bad(run(passed=0, total=0)))


class Judge(unittest.TestCase):
    def test_prompt_uses_labels_and_never_names_the_arms(self) -> None:
        prompt = judge_prompt("Fix the totals.", "## Spec\nRound half up.", "diff --git a/x", "diff --git a/y")
        self.assertIn("Fix the totals.", prompt)
        self.assertIn("Round half up.", prompt)
        self.assertIn("=== A ===\ndiff --git a/x", prompt)
        self.assertIn("=== B ===\ndiff --git a/y", prompt)
        for leak in ("workflow", "with the", "without", "skill"):
            self.assertNotIn(leak, prompt.lower(), leak)

    def test_parses_strict_json_with_or_without_a_code_fence(self) -> None:
        reply = json.dumps({"A": {"design": 3, "readability": 2, "fit": 2, "why": "x"},
                            "B": {"design": 1, "readability": 2, "fit": 2, "why": "y"}})
        expected = verdict((3, 2, 2), (1, 2, 2))
        self.assertEqual(parse_judge(reply), expected)
        self.assertEqual(parse_judge(f"```json\n{reply}\n```"), expected)

    def test_rejects_anything_else(self) -> None:
        for reply in (
            "A is better",
            json.dumps({"A": {"design": 3, "readability": 2, "fit": 2}}),
            json.dumps({"A": {"design": 4, "readability": 2, "fit": 2}, "B": {"design": 1, "readability": 2, "fit": 2}}),
            json.dumps({"A": {"design": "3", "readability": 2, "fit": 2}, "B": {"design": 1, "readability": 2, "fit": 2}}),
            json.dumps({"A": {"design": 3, "readability": 2}, "B": {"design": 1, "readability": 2, "fit": 2}}),
        ):
            self.assertIsNone(parse_judge(reply), reply)

    def test_resolving_the_two_orders(self) -> None:
        # First call: A = with, B = without. Second call: A = without, B = with.
        first = verdict((3, 2, 3), (1, 2, 1))
        agreeing_second = verdict((1, 2, 1), (3, 2, 3))
        self.assertEqual(
            resolve_judge(first, agreeing_second),
            ({"design": 3, "readability": 2, "fit": 3}, {"design": 1, "readability": 2, "fit": 1}),
        )
        # The second call prefers the without arm on design: that category becomes a tie.
        disagreeing_second = verdict((3, 2, 1), (1, 2, 3))
        self.assertEqual(
            resolve_judge(first, disagreeing_second),
            ({"design": 2, "readability": 2, "fit": 3}, {"design": 2, "readability": 2, "fit": 1}),
        )


class Report(unittest.TestCase):
    def runs(self) -> list[RunScore]:
        return [
            run("with", 4, 4, judge={"design": 3, "readability": 2, "fit": 3}, minutes=4.0, cost=1.0, index=1, refused=4),
            run("with", 2, 4, judge={"design": 2, "readability": 2, "fit": 2}, minutes=6.0, cost=1.0, index=2, refused=2),
            run("with", 4, 4, judge={"design": 3, "readability": 3, "fit": 3}, minutes=5.0, cost=1.0, index=3),
            run("without", 4, 4, judge={"design": 1, "readability": 2, "fit": 1}, minutes=2.0, cost=0.5, index=1),
            run("without", 4, 4, flags=("weakened-test",), judge={"design": 2, "readability": 2, "fit": 2}, minutes=2.0, cost=None, index=2),
            run("without", 0, 4, flags=("incomplete",), judge=None, minutes=20.0, cost=None, index=3),
        ]

    def test_summary_numbers(self) -> None:
        summary = summarize(self.runs())
        with_arm, without_arm = summary[("t", "with")], summary[("t", "without")]
        self.assertEqual(with_arm.runs, 3)
        self.assertAlmostEqual(with_arm.mean_test, 0.8333, places=4)
        self.assertAlmostEqual(with_arm.stdev_test, 0.2887, places=4)
        self.assertEqual(with_arm.worst_test, 0.5)
        self.assertAlmostEqual(with_arm.bad_rate, 1 / 3)
        self.assertAlmostEqual(with_arm.judge_means["design"] or 0, 8 / 3)
        self.assertEqual(with_arm.mean_minutes, 5.0)
        self.assertEqual(with_arm.mean_cost, 1.0)
        self.assertEqual(with_arm.mean_refused, 2.0)
        self.assertEqual(without_arm.mean_refused, 0.0)
        self.assertAlmostEqual(without_arm.mean_test, 2 / 3)
        self.assertEqual(without_arm.worst_test, 0.0)
        self.assertEqual(without_arm.bad_rate, 1.0)  # run 1 is rated worse in design and fit (AC10)
        self.assertEqual(without_arm.judge_means["design"], 1.5)  # the run without a judge score is left out
        self.assertEqual(without_arm.mean_cost, 0.5)  # only runs that reported a cost

    def test_report_text(self) -> None:
        text = format_report(summarize(self.runs()), judge_errors=1)
        self.assertIn("t\n", text)
        self.assertIn("with        3   0.83    0.29   0.50   33%     2.67   2.33  2.67    5.0  $1.00      2.0", text)
        self.assertIn("without     3   0.67    0.58   0.00  100%     1.50   2.00  1.50    8.0  $0.50      0.0", text)
        self.assertIn("refused = commands the permission allowlist refused", text)
        self.assertIn("1 judge comparison failed", text)
        self.assertIn("rough", text)


class LoadingTasks(unittest.TestCase):
    def test_the_real_tasks_file_is_valid(self) -> None:
        tasks = load_tasks(ROOT / "evals" / "quality" / "tasks.json")
        self.assertEqual([t.id for t in tasks], ["dutch-amounts", "line-discount", "reminders-cleanup"])
        for task in tasks:
            self.assertTrue((ROOT / "evals" / "quality" / "hidden" / task.id).is_dir(), task.id)

    def test_invalid_tasks_fail_loudly(self) -> None:
        for raw in (
            {},
            [{"prompt": "x", "allowed": ["a"]}],
            [{"id": "a", "allowed": ["a"]}],
            [{"id": "a", "prompt": "x"}],
            [{"id": "a", "prompt": "x", "allowed": []}],
            [{"id": "a", "prompt": "x", "allowed": ["a"]}, {"id": "a", "prompt": "y", "allowed": ["a"]}],
        ):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "tasks.json"
                path.write_text(json.dumps(raw))
                with self.assertRaises(TaskError, msg=json.dumps(raw)):
                    load_tasks(path)


if __name__ == "__main__":
    unittest.main()
