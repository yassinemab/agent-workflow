from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from install import Installer


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.home = base / "home"
        self.repo = base / "agent-workflow"
        for folder in ("skills/alpha", "agents", "global", "profiles", "hooks"):
            (self.repo / folder).mkdir(parents=True)
        (self.repo / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n")
        (self.repo / "agents" / "verifier.md").write_text("agent")
        (self.repo / "global" / "AGENTS.md").write_text("rules")
        (self.repo / "global" / "CLAUDE.md").write_text("claude rules")
        (self.repo / "profiles" / "README.md").write_text("profiles")
        settings = self.home / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(
            json.dumps({"env": {"A": "1"}, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say done"}]}]}})
        )
        (self.home / ".codex").mkdir()
        (self.home / ".codex" / "AGENTS.md").write_text("old codex rules")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def install(self, dry_run: bool = False) -> Installer:
        installer = Installer(home=self.home, repo=self.repo, dry_run=dry_run)
        self.assertEqual(installer.run(), 0, installer.problems)
        return installer

    def test_links_everything_and_keeps_other_settings(self) -> None:
        self.install()
        for link, source in (
            (".claude/skills/alpha", "skills/alpha"),
            (".agents/skills/alpha", "skills/alpha"),
            (".claude/agents/verifier.md", "agents/verifier.md"),
            (".codex/AGENTS.md", "global/AGENTS.md"),
            (".claude/project-profiles/README.md", "profiles/README.md"),
        ):
            self.assertEqual((self.home / link).resolve(), (self.repo / source).resolve(), link)

        claude_md = (self.home / ".claude" / "CLAUDE.md").read_text()
        self.assertIn(f"@{self.repo / 'global' / 'AGENTS.md'}", claude_md)
        self.assertIn(f"@{self.repo / 'global' / 'CLAUDE.md'}", claude_md)

        settings = json.loads((self.home / ".claude" / "settings.json").read_text())
        self.assertEqual(settings["env"], {"A": "1", "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"})
        agent_hooks = [g for g in settings["hooks"]["PreToolUse"] if g.get("matcher") == "Agent|Task"]
        self.assertEqual(len(agent_hooks), 1)
        stop_commands = [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]
        self.assertEqual(stop_commands[0], "say done")
        self.assertTrue(stop_commands[1].endswith('hooks/require_checks.py"'))
        self.assertEqual(settings["hooks"]["PreToolUse"][0]["matcher"], "Bash")

    def test_backs_up_replaced_files(self) -> None:
        self.install()
        backups = list((self.home / ".codex").glob("AGENTS.md.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "old codex rules")
        self.assertTrue((self.home / ".claude" / "settings.json.bak").exists())

    def test_running_twice_changes_nothing(self) -> None:
        self.install()
        settings_before = (self.home / ".claude" / "settings.json").read_text()
        second = self.install()
        self.assertEqual(second.actions, [])
        self.assertEqual((self.home / ".claude" / "settings.json").read_text(), settings_before)

    def test_dry_run_touches_nothing(self) -> None:
        installer = self.install(dry_run=True)
        self.assertTrue(installer.actions)
        self.assertFalse((self.home / ".claude" / "skills").exists())
        self.assertEqual((self.home / ".codex" / "AGENTS.md").read_text(), "old codex rules")

    def test_never_replaces_a_real_skill_folder(self) -> None:
        existing = self.home / ".claude" / "skills" / "alpha"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("user's own version")
        installer = Installer(home=self.home, repo=self.repo)
        self.assertEqual(installer.run(), 1)
        self.assertIn("is not a link", installer.problems[0])
        self.assertEqual((existing / "SKILL.md").read_text(), "user's own version")


if __name__ == "__main__":
    unittest.main()
