from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aw.evals import Case, CaseError, Observation, ToolCall, decided, grade, load_cases, observe

ROOT = Path(__file__).resolve().parent.parent
BUG = Case("bug", "the total is wrong", ("fix-bug",))
FEATURE = Case("feature", "let users export", ("scope-feature", "agent-harness"))
QUESTION = Case("question", "what does this do?", ("none",))


def assistant(*tools: tuple[str, dict[str, object]]) -> str:
    content = [{"type": "tool_use", "name": name, "input": args} for name, args in tools]
    return json.dumps({"type": "assistant", "message": {"content": content}})


def result(cost: float = 0.12, subtype: str = "success", is_error: bool = False) -> str:
    return json.dumps({"type": "result", "subtype": subtype, "is_error": is_error, "total_cost_usd": cost})


def seen(*calls: ToolCall, finished: bool = False) -> Observation:
    return Observation(calls=list(calls), finished=finished)


class Grading(unittest.TestCase):
    def test_expected_skill_first_passes(self) -> None:
        verdict = grade(seen(ToolCall("Bash"), ToolCall("Skill", "fix-bug")), BUG)
        self.assertEqual((verdict.passed, verdict.reason), (True, "used fix-bug"))

    def test_any_listed_skill_is_acceptable(self) -> None:
        self.assertTrue(grade(seen(ToolCall("Skill", "agent-harness")), FEATURE).passed)

    def test_wrong_skill_fails_and_names_both(self) -> None:
        verdict = grade(seen(ToolCall("Skill", "scope-feature")), BUG)
        self.assertEqual((verdict.passed, verdict.reason), (False, "used scope-feature, expected fix-bug"))

    def test_editing_before_any_skill_fails(self) -> None:
        verdict = grade(seen(ToolCall("Read"), ToolCall("Edit"), ToolCall("Skill", "fix-bug")), BUG)
        self.assertEqual((verdict.passed, verdict.reason), (False, "tried Edit before loading a skill"))

    def test_no_skill_at_all_fails(self) -> None:
        verdict = grade(seen(ToolCall("Read"), ToolCall("Grep"), finished=True), FEATURE)
        self.assertEqual((verdict.passed, verdict.reason), (False, "no skill within 2 tool call(s)"))

    def test_none_cases_pass_without_a_skill_even_with_edits(self) -> None:
        self.assertTrue(grade(seen(ToolCall("Read"), ToolCall("Edit"), finished=True), QUESTION).passed)
        self.assertFalse(grade(seen(ToolCall("Skill", "scope-feature")), QUESTION).passed)

    def test_a_failed_run_fails(self) -> None:
        verdict = grade(Observation(error="error_during_execution"), BUG)
        self.assertEqual(verdict.reason, "run failed: error_during_execution")


class StoppingEarly(unittest.TestCase):
    def test_stops_at_the_first_skill_or_forbidden_edit(self) -> None:
        self.assertFalse(decided(seen(ToolCall("Read")), BUG, max_calls=8))
        self.assertTrue(decided(seen(ToolCall("Skill", "fix-bug")), BUG, max_calls=8))
        self.assertTrue(decided(seen(ToolCall("Write")), BUG, max_calls=8))
        self.assertTrue(decided(seen(ToolCall("Read"), ToolCall("Read")), BUG, max_calls=2))

    def test_none_cases_run_to_the_end_unless_a_skill_appears(self) -> None:
        self.assertFalse(decided(seen(ToolCall("Edit")), QUESTION, max_calls=8))
        self.assertTrue(decided(seen(ToolCall("Skill", "fix-bug")), QUESTION, max_calls=8))

    def test_observe_reads_until_decided_and_ignores_noise(self) -> None:
        lines = [
            "not json",
            json.dumps({"type": "system", "subtype": "init"}),
            assistant(("Bash", {"command": "ls"})),
            assistant(("Skill", {"skill": "fix-bug", "args": "x"})),
            assistant(("Edit", {"file_path": "a.py"})),
        ]
        observation = observe(iter(lines), BUG, max_calls=8)
        self.assertEqual([c.name for c in observation.calls], ["Bash", "Skill"])
        self.assertEqual(observation.calls[1].skill, "fix-bug")

    def test_observe_records_cost_and_errors(self) -> None:
        done = observe(iter([assistant(("Read", {})), result(0.5)]), QUESTION, max_calls=8)
        self.assertEqual((done.finished, done.cost_usd, done.error), (True, 0.5, None))
        failed = observe(iter([result(0.1, "error_during_execution", True)]), BUG, max_calls=8)
        self.assertEqual(failed.error, "error_during_execution")
        over_budget = observe(iter([result(1.0, "error_max_budget_usd", True)]), BUG, max_calls=8)
        self.assertIsNone(over_budget.error)


class LoadingCases(unittest.TestCase):
    def test_the_real_cases_file_is_valid(self) -> None:
        cases = load_cases(ROOT / "evals" / "cases.json")
        self.assertGreaterEqual(len(cases), 15)
        self.assertTrue(any(c.expects_no_skill for c in cases))

    def test_invalid_cases_fail_loudly(self) -> None:
        for raw in (
            {},
            [{"prompt": "x", "expect_skill": "fix-bug"}],
            [{"id": "a", "expect_skill": "fix-bug"}],
            [{"id": "a", "prompt": "x"}],
            [{"id": "a", "prompt": "x", "expect_skill": []}],
            [{"id": "a", "prompt": "x", "expect_skill": "s"}, {"id": "a", "prompt": "y", "expect_skill": "s"}],
        ):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "cases.json"
                path.write_text(json.dumps(raw))
                with self.assertRaises(CaseError, msg=json.dumps(raw)):
                    load_cases(path)


if __name__ == "__main__":
    unittest.main()
