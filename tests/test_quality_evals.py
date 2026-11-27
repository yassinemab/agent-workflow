"""bin/run-quality-evals end to end, with a fake `claude` playing both the agent and the judge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time
STARTED = time.time()
args = sys.argv
prompt = args[args.index("-p") + 1]
arm = "without" if "--disable-slash-commands" in args else "with"
log = pathlib.Path(os.environ["AW_FAKE_LOG"])

def result(subtype="success", cost=0.25, text="", denials=0):
    print(json.dumps({"type": "result", "subtype": subtype, "is_error": subtype != "success",
                      "total_cost_usd": cost, "result": text,
                      "permission_denials": [{"tool_name": "Bash"}] * denials}), flush=True)

if "--tools" in args:  # the judge
    cwd_entries = sorted(os.listdir("."))
    time.sleep(0.3)
    with log.open("a") as f:
        f.write(json.dumps({"judge": True, "args": args[1:], "prompt": prompt, "cwd": os.getcwd(),
                            "cwd_entries": cwd_entries, "start": STARTED, "end": time.time()}) + "\n")
    mode = os.environ.get("AW_FAKE_JUDGE", "prefer-fix")
    a, b = prompt.split("=== A ===", 1)[1].split("=== B ===", 1)
    import hashlib
    attempts = log.with_suffix(".attempts-" + hashlib.sha1(prompt.encode()).hexdigest()[:12])  # per order, so parallel calls don't race
    count = int(attempts.read_text()) if attempts.exists() else 0
    attempts.write_text(str(count + 1))
    if mode == "invalid" or (mode == "invalid-once" and count % 2 == 0):
        result(text="A looks better to me.")
    elif mode == "prefer-first":
        result(text=json.dumps({"A": {"design": 3, "readability": 3, "fit": 3, "why": "a"},
                                "B": {"design": 1, "readability": 1, "fit": 1, "why": "b"}}))
    else:  # prefer whichever diff contains the full fix
        fix = 'replace(".", "")'
        good, bad = {"design": 3, "readability": 2, "fit": 3, "why": "x"}, {"design": 1, "readability": 2, "fit": 1, "why": "y"}
        result(text=json.dumps({"A": good, "B": bad} if fix in a else {"A": bad, "B": good} if fix in b else
                               {"A": dict(bad, design=2, fit=2), "B": dict(bad, design=2, fit=2)}))
    sys.exit(0)

hidden_present = any(pathlib.Path("tests").glob("test_hidden_*.py"))
with log.open("a") as f:
    f.write(json.dumps({"arm": arm, "args": args[1:], "hidden_present": hidden_present, "prompt": prompt,
                        "start": STARTED}) + "\n")
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {}}]}}), flush=True)

if "1,5" in prompt:  # dutch-amounts
    invoice = pathlib.Path("billing/invoice.py")
    old = 'return Decimal(text.replace(",", ""))'
    marker = f"# session {os.getpid()}-{STARTED}\n"  # makes every session's diff unique
    invoice.write_text(marker + invoice.read_text())
    if arm == "with":
        invoice.write_text(invoice.read_text().replace(old, 'return Decimal(text.replace(".", "").replace(",", "."))'))
    else:  # a half fix, a weakened visible test, and a file outside the task
        invoice.write_text(invoice.read_text().replace(old, 'return Decimal(text.replace(",", "."))'))
        test = pathlib.Path("tests/test_invoice.py")
        test.write_text(test.read_text().replace('self.assertEqual(invoice_total([("10", 2)]), 20)', "pass"))
        pathlib.Path("setup.py").write_text("x = 1\n")
    result(denials=2 if arm == "without" else 0)
elif "messy" in prompt and arm == "without":  # reminders-cleanup: deletes tests/, then crashes
    import shutil
    shutil.rmtree("tests")
    sys.exit(1)
elif "discount" in prompt and arm == "without":  # line-discount: renames and weakens a test, runs out of budget
    old_test = pathlib.Path("tests/test_invoice.py")
    text = old_test.read_text().replace('self.assertEqual(invoice_total([("10", 2)]), 20)', "pass")
    old_test.unlink()
    pathlib.Path("tests/test_invoice_totals.py").write_text(text)
    result(subtype="error_max_budget_usd")
else:  # line-discount and reminders-cleanup in the with arm: change nothing
    if "messy" in prompt:  # the slowest session of the run
        time.sleep(1.5)
        with log.open("a") as f:
            f.write(json.dumps({"slow_session_end": time.time()}) + "\n")
    result(cost=0.5)
'''


class QualityEvalHarness(unittest.TestCase):
    """Runs the command once per class and lets each test inspect the outcome."""

    runs = 5
    judge_mode = "prefer-fix"
    extra_args: tuple[str, ...] = ()

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        fake = base / "claude"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        cls.log = base / "calls.jsonl"
        cls.state = base / "state"
        env = {
            **os.environ,
            "AW_CLAUDE_BIN": str(fake),
            "AW_FAKE_LOG": str(cls.log),
            "AW_FAKE_JUDGE": cls.judge_mode,
            "AW_STATE_DIR": str(cls.state),
        }
        cls.result = subprocess.run(
            [sys.executable, str(ROOT / "bin" / "run-quality-evals"), "--jobs", "6", *cls.extra_args]
            + ([] if cls.runs == 5 else ["--runs", str(cls.runs)]),
            capture_output=True, text=True, env=env, timeout=300, check=False,
        )
        calls = [json.loads(line) for line in cls.log.read_text().splitlines()] if cls.log.exists() else []
        cls.slow_ends = [c["slow_session_end"] for c in calls if "slow_session_end" in c]
        calls = [c for c in calls if "slow_session_end" not in c]
        cls.sessions = [c for c in calls if not c.get("judge")]
        cls.judge_calls = [c for c in calls if c.get("judge")]
        folders = sorted((cls.state / "quality-evals").glob("*")) if (cls.state / "quality-evals").exists() else []
        cls.folder = folders[-1] if folders else cls.state / "missing"
        results = cls.folder / "results.json"
        cls.results = json.loads(results.read_text()) if results.exists() else {"runs": []}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def runs_of(self, task: str, arm: str) -> list[dict[str, object]]:
        found = [r for r in self.results["runs"] if r["task"] == task and r["arm"] == arm]
        self.assertTrue(found, f"no {arm} runs of {task} in results.json; output:\n{self.result.stdout}{self.result.stderr}")
        return found


class SessionsAndScoring(QualityEvalHarness):
    def test_runs_every_task_five_times_per_arm_on_sonnet(self) -> None:
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)
        self.assertEqual(len(self.sessions), 30)
        for call in self.sessions:
            args = call["args"]
            self.assertEqual(args[args.index("--model") + 1], "sonnet")
        per_task = {}
        for call in self.sessions:
            key = (call["prompt"][:20], call["arm"])
            per_task[key] = per_task.get(key, 0) + 1
        self.assertEqual(sorted(per_task.values()), [5] * 6)

    def test_without_arm_loads_no_user_settings_or_skills(self) -> None:
        for call in self.sessions:
            args = call["args"]
            if call["arm"] == "without":
                self.assertEqual(args[args.index("--setting-sources") + 1], "project")
                self.assertIn("--disable-slash-commands", args)
            else:
                self.assertNotIn("--setting-sources", args)
                self.assertNotIn("--disable-slash-commands", args)

    def test_sessions_run_with_the_allowlist_only(self) -> None:
        expected = [
            "Skill", "Agent", "Read", "Glob", "Grep", "Edit", "Write",
            "Bash(python3 *)", "Bash(cd *)", "Bash(ls*)", "Bash(find *)", "Bash(cat *)", "Bash(mkdir *)",
            "Bash(which *)", "Bash(git status*)", "Bash(git diff*)",
            "Bash(~/agent-workflow/bin/run-checks*)", f"Bash({ROOT}/bin/run-checks*)",
        ]
        for call in self.sessions:
            args = call["args"]
            self.assertEqual(args[args.index("--permission-mode") + 1], "dontAsk")
            self.assertEqual(args[args.index("--allowedTools") + 1].split(","), expected)
            self.assertEqual(
                args[args.index("--disallowedTools") + 1].split(","),
                ["Read(~/agent-workflow/evals/**)", "Grep(~/agent-workflow/evals/**)", "Glob(~/agent-workflow/evals/**)"],
            )
            self.assertNotIn("bypassPermissions", args)
            self.assertNotIn("--dangerously-skip-permissions", args)

    def test_hidden_tests_are_absent_during_the_session_and_scored_after(self) -> None:
        self.assertFalse(any(c["hidden_present"] for c in self.sessions))
        for run in self.runs_of("dutch-amounts", "with"):
            self.assertEqual((run["tests_passed"], run["tests_total"]), (5, 5))
        for run in self.runs_of("dutch-amounts", "without"):
            self.assertEqual(run["tests_total"], 5)
            self.assertLess(run["tests_passed"], 5)  # "1.234,56" still fails with the half fix
        for run in self.runs_of("reminders-cleanup", "with"):
            self.assertEqual(run["tests_passed"], run["tests_total"])  # unchanged code keeps its behavior

    def test_flags_a_weakened_test(self) -> None:
        for run in self.runs_of("dutch-amounts", "without"):
            self.assertIn("weakened-test", run["flags"])
        for run in self.runs_of("dutch-amounts", "with"):
            self.assertNotIn("weakened-test", run["flags"])

    def test_flags_out_of_scope_changes(self) -> None:
        for run in self.runs_of("dutch-amounts", "without"):
            self.assertIn("out-of-scope", run["flags"])
        for run in self.runs_of("dutch-amounts", "with"):
            self.assertEqual(run["flags"], [])

    def test_flags_incomplete_runs(self) -> None:
        crashed = self.runs_of("reminders-cleanup", "without")  # deleted tests/, then crashed
        self.assertEqual(len(crashed), 5)
        for run in crashed:
            self.assertIn("incomplete", run["flags"])
            self.assertTrue(run["bad"])
            self.assertEqual((run["tests_passed"], run["tests_total"]), (0, 9))
        for run in self.runs_of("line-discount", "without"):  # ran out of budget
            self.assertIn("incomplete", run["flags"])

    def test_a_renamed_and_weakened_test_is_still_caught(self) -> None:
        for run in self.runs_of("line-discount", "without"):
            self.assertIn("weakened-test", run["flags"])
        for run in self.runs_of("line-discount", "with"):
            self.assertEqual(run["flags"], [])

    def test_saves_every_step(self) -> None:
        self.assertTrue((self.folder / "results.json").is_file())
        for run in self.results["runs"]:
            run_dir = self.folder / str(run["task"]) / f"{run['arm']}-{run['index']}"
            for name in ("transcript.jsonl", "diff.patch", "hidden-tests.txt"):
                self.assertTrue((run_dir / name).is_file(), run_dir / name)
        self.assertTrue(list((self.folder / "judge").glob("*.txt")))

    def test_sessions_are_bounded_and_announced(self) -> None:
        self.assertIn("30 sessions", self.result.stdout.splitlines()[0])
        for call in self.sessions:
            args = call["args"]
            self.assertEqual(args[args.index("--max-budget-usd") + 1], "3.0")
        self.assertIn("timeout 20 min", self.result.stdout.splitlines()[0])

    def test_counts_refused_commands(self) -> None:
        for run in self.runs_of("dutch-amounts", "without"):
            self.assertEqual(run["refused"], 2)
        for run in self.runs_of("dutch-amounts", "with"):
            self.assertEqual(run["refused"], 0)

    def test_the_with_arm_starts_first(self) -> None:
        first = sorted(self.sessions, key=lambda c: c["start"])[:6]  # --jobs 6
        self.assertEqual([c["arm"] for c in first], ["with"] * 6)

    def test_judging_doesnt_wait_for_the_slowest_session(self) -> None:
        dutch_judging = [c["start"] for c in self.judge_calls if "1,5" in c["prompt"]]
        self.assertTrue(dutch_judging and self.slow_ends)
        self.assertLess(min(dutch_judging), max(self.slow_ends))

    def test_both_orders_of_a_pair_are_judged_at_the_same_time(self) -> None:
        def pair_key(call: dict[str, object]) -> tuple[str, ...]:
            a, b = str(call["prompt"]).split("=== A ===", 1)[1].split("=== B ===", 1)
            return tuple(sorted((a.strip(), b.strip())))  # the same two diffs, in either order

        pairs: dict[tuple[str, ...], list[dict[str, object]]] = {}
        for call in (c for c in self.judge_calls if "1,5" in str(c["prompt"])):
            pairs.setdefault(pair_key(call), []).append(call)
        self.assertTrue(pairs)
        for calls in pairs.values():
            self.assertEqual(len(calls), 2)
            first, second = sorted(calls, key=lambda c: float(c["start"]))
            self.assertLess(float(second["start"]), float(first["end"]))  # the second started before the first ended

    def test_prints_the_report(self) -> None:
        self.assertIn("dutch-amounts\n", self.result.stdout)
        self.assertIn("rough spread", self.result.stdout)


class Judging(QualityEvalHarness):
    runs = 2
    extra_args = ("--task", "dutch-amounts")

    def test_judge_is_blind_order_swapped_and_resolves_disagreement(self) -> None:
        self.assertEqual(len(self.judge_calls), 4)  # 2 pairs, each judged in both orders
        for call in self.judge_calls:
            args = call["args"]
            self.assertEqual(args[args.index("--tools") + 1], "")
            self.assertIn("--disable-slash-commands", args)
            prompt = str(call["prompt"]).lower()
            self.assertNotIn("without", prompt)
            self.assertNotIn("workflow", prompt)
            self.assertNotIn("setup.py", prompt)  # only code and test diffs reach the judge
            self.assertEqual(call["cwd_entries"], [])  # an empty folder: no project settings to load
            self.assertNotEqual(Path(call["cwd"]).resolve(), Path.cwd().resolve())
        for run in self.runs_of("dutch-amounts", "with"):
            self.assertEqual(run["judge"], {"design": 3, "readability": 2, "fit": 3})
        for run in self.runs_of("dutch-amounts", "without"):
            self.assertEqual(run["judge"], {"design": 1, "readability": 2, "fit": 1})


class JudgeOrderBias(QualityEvalHarness):
    runs = 1
    judge_mode = "prefer-first"
    extra_args = ("--task", "dutch-amounts")

    def test_a_judge_that_always_prefers_the_first_answer_resolves_to_ties(self) -> None:
        for run in self.results["runs"]:
            self.assertEqual(run["judge"], {"design": 2, "readability": 2, "fit": 2})


class InvalidJudgeOnce(QualityEvalHarness):
    runs = 1
    judge_mode = "invalid-once"
    extra_args = ("--task", "dutch-amounts")

    def test_invalid_judge_output_is_retried_once_then_flagged(self) -> None:
        self.assertEqual(len(self.judge_calls), 4)  # each order: one invalid reply, one retry
        for run in self.results["runs"]:
            self.assertIsNotNone(run["judge"])
            self.assertFalse(run["judge_error"])


class InvalidJudgeAlways(QualityEvalHarness):
    runs = 1
    judge_mode = "invalid"
    extra_args = ("--task", "dutch-amounts")

    def test_a_judge_that_never_answers_properly_flags_the_pair(self) -> None:
        self.assertEqual(len(self.judge_calls), 4)  # two orders, two attempts each, no more
        for run in self.results["runs"]:
            self.assertIsNone(run["judge"])
            self.assertTrue(run["judge_error"])
        self.assertIn("1 judge comparison failed", self.result.stdout)


if __name__ == "__main__":
    unittest.main()
