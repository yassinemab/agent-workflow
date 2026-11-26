"""End-to-end tests: run the real hook scripts and run-checks against a temporary repo."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


class HookHarness(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.repo = base / "project"
        self.repo.mkdir()
        self.home = base / "home"
        (self.home / "agent-workflow" / "global").mkdir(parents=True)
        self.profiles = base / "profiles"
        self.profiles.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "app.py").write_text("x = 1\n")
        (self.repo / "README.md").write_text("readme\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")
        self.env = {
            **os.environ,
            "AW_PROFILES_DIR": str(self.profiles),
            "AW_USER_HOME": str(self.home),
            "AW_STATE_DIR": str(base / "state"),
        }

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_config(self, config: dict[str, object]) -> None:
        (self.repo / ".claude").mkdir(exist_ok=True)
        (self.repo / ".claude" / "workflow.json").write_text(json.dumps(config))
        git(self.repo, "add", ".claude")
        git(self.repo, "commit", "-q", "-m", "config")

    def hook(self, script: str, payload: dict[str, object]) -> dict[str, object] | None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "hooks" / script)],
            input=json.dumps({"cwd": str(self.repo), "session_id": "s1", **payload}),
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def run_checks(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "bin" / "run-checks")],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )


class RequireChecksHook(HookHarness):
    def test_full_turn_cycle(self) -> None:
        self.write_config({"checks": [{"name": "unit", "run": "test -f app.py"}]})
        self.assertIsNone(self.hook("track_turn.py", {"prompt": "go"}))

        # Nothing changed: the turn may end.
        self.assertIsNone(self.hook("require_checks.py", {"stop_hook_active": False}))

        # Code changed and no checks ran: blocked.
        (self.repo / "app.py").write_text("x = 2\n")
        blocked = self.hook("require_checks.py", {"stop_hook_active": False})
        assert blocked is not None
        self.assertEqual(blocked["decision"], "block")
        self.assertIn("app.py", str(blocked["reason"]))

        # The checks pass on the current state: allowed.
        result = self.run_checks()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS  unit", result.stdout)
        self.assertIsNone(self.hook("require_checks.py", {"stop_hook_active": False}))

        # A further edit after the run: blocked again.
        (self.repo / "new_module.py").write_text("y = 1\n")
        self.assertIsNotNone(self.hook("require_checks.py", {"stop_hook_active": True}))

    def test_doc_only_changes_need_no_checks(self) -> None:
        self.write_config({"checks": [{"name": "unit", "run": "true"}]})
        self.hook("track_turn.py", {"prompt": "go"})
        (self.repo / "README.md").write_text("better readme\n")
        self.assertIsNone(self.hook("require_checks.py", {"stop_hook_active": False}))

    def test_failing_checks_are_recorded_and_reported_once(self) -> None:
        self.write_config({"checks": [{"name": "unit", "run": "exit 3"}]})
        self.hook("track_turn.py", {"prompt": "go"})
        (self.repo / "app.py").write_text("x = 2\n")
        result = self.run_checks()
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL  unit", result.stdout)
        blocked = self.hook("require_checks.py", {"stop_hook_active": False})
        assert blocked is not None
        self.assertIn("failed on the current state: unit", str(blocked["reason"]))
        self.assertIsNone(self.hook("require_checks.py", {"stop_hook_active": True}))

    def test_a_hung_check_times_out_and_fails(self) -> None:
        self.write_config({"checks": [{"name": "hangs", "run": "sleep 300", "timeout_minutes": 0.02}]})
        result = self.run_checks()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL  hangs", result.stdout)
        self.assertIn("timed out after 0.02 min", result.stdout)

    def test_outside_git_does_nothing(self) -> None:
        outside = Path(self._tmp.name) / "plain"
        outside.mkdir()
        payload = {"cwd": str(outside)}
        self.assertIsNone(self.hook("track_turn.py", payload))
        self.assertIsNone(self.hook("require_checks.py", payload))

    def test_run_checks_without_config_explains_what_to_do(self) -> None:
        result = self.run_checks()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no checks configured", result.stderr)


class GuardCommandsHook(HookHarness):
    def test_denies_with_a_reason(self) -> None:
        output = self.hook("guard_commands.py", {"tool_name": "Bash", "tool_input": {"command": "git push"}})
        assert output is not None
        decision = output["hookSpecificOutput"]
        assert isinstance(decision, dict)
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("protected branch", decision["permissionDecisionReason"])

    def test_project_blocked_commands_apply(self) -> None:
        self.write_config({"blocked_commands": [{"pattern": "mysqldump", "reason": "Locks tables."}]})
        output = self.hook(
            "guard_commands.py", {"tool_name": "Bash", "tool_input": {"command": "mysqldump db"}}
        )
        assert output is not None
        self.assertIn("Locks tables.", json.dumps(output))

    def test_allows_normal_commands_silently(self) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
        self.assertIsNone(self.hook("guard_commands.py", payload))


class CrashesAndTheEventLog(HookHarness):
    def raw_hook(self, script: str, stdin: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "hooks" / script)],
            input=stdin, capture_output=True, text=True, env=self.env, check=False,
        )

    def events(self) -> list[dict[str, object]]:
        path = Path(self.env["AW_STATE_DIR"]) / "events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_a_crashing_guard_denies_instead_of_letting_the_call_through(self) -> None:
        for script in ("guard_commands.py", "guard_rule_files.py", "guard_subagent_model.py"):
            result = self.raw_hook(script, "not json")
            self.assertEqual(result.returncode, 0, script)
            self.assertIn('"permissionDecision": "deny"', result.stdout, script)
            self.assertIn("crashed", result.stdout, script)

    def test_other_hooks_report_a_crash_without_blocking(self) -> None:
        result = self.raw_hook("track_turn.py", "not json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_decisions_and_crashes_are_logged(self) -> None:
        self.hook("guard_commands.py", {"tool_name": "Bash", "tool_input": {"command": "git stash"}})
        self.raw_hook("guard_subagent_model.py", "not json")
        logged = [(e["hook"], e["decision"]) for e in self.events()]
        self.assertIn(("guard-commands", "deny"), logged)
        self.assertIn(("guard-subagent-model", "crash"), logged)
        self.assertEqual(self.events()[0]["cwd"], str(self.repo))

    def test_a_broken_project_config_keeps_the_global_rules_and_is_logged(self) -> None:
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "workflow.json").write_text("{broken")
        denied = self.hook("guard_commands.py", {"tool_name": "Bash", "tool_input": {"command": "git stash"}})
        self.assertIn("guard-commands", json.dumps(denied))
        self.assertIsNone(self.hook("guard_commands.py", {"tool_name": "Bash", "tool_input": {"command": "ls"}}))
        self.assertIn("config-error", [e["decision"] for e in self.events()])


class GuardRuleFilesHook(HookHarness):
    def decision(self, tool: str, tool_input: dict[str, object], mode: str = "default") -> str | None:
        output = self.hook(
            "guard_rule_files.py", {"tool_name": tool, "tool_input": tool_input, "permission_mode": mode}
        )
        if output is None:
            return None
        specific = output["hookSpecificOutput"]
        assert isinstance(specific, dict)
        return str(specific["permissionDecision"])

    def test_asks_before_changing_any_workflow_file_in_normal_modes(self) -> None:
        for target in (
            self.home / "agent-workflow" / "global" / "AGENTS.md",
            self.home / "agent-workflow" / "hooks" / "guard_rule_files.py",
            self.home / ".claude" / "CLAUDE.md",
            self.home / ".claude" / "settings.json",
        ):
            self.assertEqual(self.decision("Edit", {"file_path": str(target)}), "ask", target)

    def test_bypass_mode_leaves_it_to_the_chat_approval_rule(self) -> None:
        target = {"file_path": str(self.home / "agent-workflow" / "global" / "AGENTS.md")}
        self.assertIsNone(self.decision("Write", target, "bypassPermissions"))

    def test_project_files_are_not_protected(self) -> None:
        for target in (self.repo / ".claude" / "CLAUDE.md", self.repo / "app.py"):
            self.assertIsNone(self.decision("Write", {"file_path": str(target)}))

    def test_shell_writes_are_caught_and_reads_and_runs_are_not(self) -> None:
        self.assertEqual(self.decision("Bash", {"command": "echo rule >> ~/agent-workflow/global/AGENTS.md"}), "ask")
        self.assertEqual(self.decision("Bash", {"command": "sed -i '' 's/a/b/' ~/.claude/settings.json"}), "ask")
        for command in (
            "cat ~/agent-workflow/global/AGENTS.md",
            "cd ~/agent-workflow && python3 -m unittest discover -s tests -t .",
            "~/agent-workflow/bin/run-checks > /tmp/log.txt 2>&1",
        ):
            self.assertIsNone(self.decision("Bash", {"command": command}), command)


class FlagTestEditsHook(HookHarness):
    def test_warns_on_an_edit_that_removes_an_assertion(self) -> None:
        payload = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(self.repo / "tests" / "test_app.py"),
                "old_string": "assert total == 10\nassert count == 2",
                "new_string": "assert total == 10",
            },
        }
        output = self.hook("flag_test_edits.py", payload)
        assert output is not None
        self.assertEqual(output["decision"], "block")
        self.assertIn("removed 1 assertion(s)", str(output["reason"]))

    def test_write_is_compared_with_the_committed_file(self) -> None:
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_app.py").write_text("def test_a():\n    assert f() == 1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "tests")
        payload = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(tests / "test_app.py"),
                "content": "import pytest\n\n@pytest.mark.skip\ndef test_a():\n    assert f() == 1\n",
            },
        }
        output = self.hook("flag_test_edits.py", payload)
        assert output is not None
        self.assertIn("added 1 skip", str(output["reason"]))

    def test_ignores_non_test_files_and_new_tests(self) -> None:
        edit = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(self.repo / "app.py"), "old_string": "assert x", "new_string": ""},
        }
        self.assertIsNone(self.hook("flag_test_edits.py", edit))
        new_file = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.repo / "tests" / "test_new.py"), "content": "x = 1"},
        }
        self.assertIsNone(self.hook("flag_test_edits.py", new_file))


if __name__ == "__main__":
    unittest.main()
