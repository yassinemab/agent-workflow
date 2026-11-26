from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aw.writes import command_writes_protected, is_protected

NAMES = ("agent-workflow",)


class ProtectedPaths(unittest.TestCase):
    def test_paths_inside_or_linked_into_the_protected_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "global"
            protected.mkdir()
            (protected / "AGENTS.md").write_text("rules")
            link = Path(tmp) / "AGENTS.md"
            link.symlink_to(protected / "AGENTS.md")
            self.assertTrue(is_protected(protected / "AGENTS.md", protected))
            self.assertTrue(is_protected(link, protected))
            self.assertTrue(is_protected(protected, protected))
            self.assertFalse(is_protected(Path(tmp) / "other.md", protected))


class ShellWrites(unittest.TestCase):
    def test_writes_into_protected_paths_are_caught(self) -> None:
        for command in (
            "echo x >> ~/agent-workflow/global/AGENTS.md",
            "echo x >~/agent-workflow/global/AGENTS.md",
            "sed -i '' 's/a/b/' agent-workflow/global/x.md",
            "perl -pi -e 's/a/b/' ~/agent-workflow/global/AGENTS.md",
            "cat a | tee -a ~/agent-workflow/global/AGENTS.md",
            "cp /tmp/new.md ~/agent-workflow/global/AGENTS.md",
            "cp x.md ~/agent-workflow/global/",
            "cd /tmp && cp new.md ~/agent-workflow/skills/x/SKILL.md",
            "mv ~/agent-workflow/hooks/guard.py /tmp/",
            "rm -rf ~/agent-workflow/hooks",
            "ln -sf /tmp/fake.py ~/agent-workflow/hooks/guard.py",
            "dd if=/tmp/x of=/Users/me/agent-workflow/global/AGENTS.md",
            "bash -c 'echo x >> ~/agent-workflow/global/AGENTS.md'",
            "python3 -c 'open(\"agent-workflow/global/x\",\"w\")'",
            "git -C ~/agent-workflow checkout -- global/AGENTS.md",
        ):
            self.assertTrue(command_writes_protected(command, NAMES), command)

    def test_reads_runs_and_writes_elsewhere_are_not(self) -> None:
        for command in (
            "cat ~/agent-workflow/global/AGENTS.md 2>&1",
            "sed -n 1,5p agent-workflow/global/AGENTS.md",
            "echo x > other.md",
            "~/agent-workflow/bin/run-checks > /tmp/claude/log.txt 2>&1",
            "cd ~/agent-workflow && bin/run-checks 2>&1 | tail -5",
            "cd agent-workflow/global && python3 -m unittest",
            "cp ~/agent-workflow/global/AGENTS.md /tmp/copy.md",
            "grep -rn rule ~/agent-workflow/skills > /tmp/hits.txt",
            "diff ~/agent-workflow/global/AGENTS.md /tmp/old.md",
            "python3 -c 'import json; print(1)' && ls ~/agent-workflow",
            "cat > /tmp/readme.md <<'EOF'\nsee ~/agent-workflow/evals\nEOF",
            "sed -n '1,20p' ~/agent-workflow/aw/guards.py | tee /tmp/guards.py",
            "git -C ~/agent-workflow log --oneline",
        ):
            self.assertFalse(command_writes_protected(command, NAMES), command)


if __name__ == "__main__":
    unittest.main()
