from __future__ import annotations

import unittest

from aw.subagents import check_subagent


class SubagentsRunOnCheaperModels(unittest.TestCase):
    def test_expensive_models_are_denied(self) -> None:
        for model in ("opus", "fable", "claude-opus-5-5", "claude-fable-5-2", "Opus"):
            verdict = check_subagent({"subagent_type": "general-purpose", "model": model})
            self.assertFalse(verdict.allowed, model)
            self.assertIn("sonnet", verdict.reason)

    def test_forks_are_denied_because_they_always_use_the_main_model(self) -> None:
        verdict = check_subagent({"subagent_type": "fork", "prompt": "do x"})
        self.assertFalse(verdict.allowed)
        self.assertIn("fresh subagent", verdict.reason)

    def test_cheaper_or_default_models_are_allowed(self) -> None:
        for tool_input in (
            {"subagent_type": "general-purpose", "model": "sonnet"},
            {"subagent_type": "Explore", "model": "haiku"},
            {"subagent_type": "standards-reviewer"},
            {"prompt": "no type at all"},
        ):
            self.assertTrue(check_subagent(tool_input).allowed, tool_input)


if __name__ == "__main__":
    unittest.main()
