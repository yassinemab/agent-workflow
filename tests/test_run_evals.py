"""run-evals end to end, with a fake `claude` that prints canned stream-json."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, sys, time
prompt = sys.argv[sys.argv.index("-p") + 1]
def say(*tools):
    content = [{"type": "tool_use", "name": n, "input": a} for n, a in tools]
    print(json.dumps({"type": "assistant", "message": {"content": content}}), flush=True)
say(("Bash", {"command": "ls"}))
if "1,5" in prompt:
    say(("Skill", {"skill": "fix-bug"}))
    time.sleep(30)  # the runner must stop here instead of waiting
elif "discount" in prompt:
    say(("Edit", {"file_path": "billing/invoice.py"}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": 0.05}), flush=True)
"""


class RunEvals(unittest.TestCase):
    def test_runs_cases_grades_them_and_stops_early(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "claude"
            fake.write_text(FAKE_CLAUDE)
            fake.chmod(0o755)
            env = {**os.environ, "AW_CLAUDE_BIN": str(fake), "AW_STATE_DIR": tmp}
            result = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "run-evals"),
                 "--case", "bug-indirect", "--case", "feature-direct", "--case", "question-only"],
                capture_output=True, text=True, env=env, timeout=25, check=False,
            )
            out = result.stdout
            self.assertEqual(result.returncode, 1, out + result.stderr)
            self.assertIn("PASS  bug-indirect", out)
            self.assertIn("FAIL  feature-direct", out)
            self.assertIn("tried Edit before loading a skill", out)
            self.assertIn("PASS  question-only", out)
            self.assertIn("2/3 passed", out)
            reports = list((Path(tmp) / "evals").glob("*.json"))
            self.assertEqual(len(reports), 1)
            outcomes = json.loads(reports[0].read_text())["outcomes"]
            self.assertEqual({o["case_id"] for o in outcomes}, {"bug-indirect", "feature-direct", "question-only"})

    def test_unknown_case_is_an_error(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "bin" / "run-evals"), "--case", "nope"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown case(s): nope", result.stderr)


if __name__ == "__main__":
    unittest.main()
