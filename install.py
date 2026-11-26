#!/usr/bin/env python3
"""Link ~/agent-workflow into Claude Code and Codex. Safe to run again.

Usage: python3 install.py [--dry-run]

- skills/<name>/      -> ~/.claude/skills/<name> and ~/.agents/skills/<name> (Codex)
- agents/<name>.md    -> ~/.claude/agents/<name>.md
- global/AGENTS.md    -> ~/.codex/AGENTS.md
- ~/.claude/CLAUDE.md    imports global/AGENTS.md and global/CLAUDE.md
- profiles/README.md  -> ~/.claude/project-profiles/README.md
- hooks/*             registered in ~/.claude/settings.json (other hooks are kept)
- CLAUDE_CODE_SUBAGENT_MODEL=sonnet in ~/.claude/settings.json `env`

An existing file that would be replaced is backed up next to itself first. An
existing real skill folder is never replaced: move it into skills/ yourself.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

REPO = Path(__file__).resolve().parent
MARKER = "agent-workflow/hooks/"

# (event, matcher or None, script)
HOOKS: tuple[tuple[str, str | None, str], ...] = (
    ("UserPromptSubmit", None, "track_turn.py"),
    ("Stop", None, "require_checks.py"),
    ("PreToolUse", "Bash", "guard_commands.py"),
    ("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit|Bash", "guard_rule_files.py"),
    ("PostToolUse", "Edit|Write|MultiEdit", "flag_test_edits.py"),
    ("PreToolUse", "Agent|Task", "guard_subagent_model.py"),
)
# Subagents without an explicit model run on this one (AGENTS.md section 1).
ENV = {"CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"}


@dataclass
class Installer:
    home: Path
    repo: Path = REPO
    dry_run: bool = False
    actions: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def _do(self, message: str) -> bool:
        self.actions.append(message)
        return not self.dry_run

    def _backup(self, path: Path) -> None:
        backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        if self._do(f"back up {path} -> {backup.name}"):
            shutil.move(str(path), backup)

    def link(self, target: Path, source: Path, *, replace_files: bool = True) -> None:
        if target.is_symlink():
            if target.resolve() == source.resolve():
                return
            if self._do(f"relink {target} -> {source}"):
                target.unlink()
                target.symlink_to(source)
            return
        if target.exists():
            if target.is_dir() or not replace_files:
                self.problems.append(f"{target} exists and is not a link; move it into {self.repo} first")
                return
            self._backup(target)
        if self._do(f"link {target} -> {source}"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source)

    def write_file(self, target: Path, content: str) -> None:
        if target.is_file() and not target.is_symlink() and target.read_text() == content:
            return
        if target.exists() or target.is_symlink():
            self._backup(target)
        if self._do(f"write {target}"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

    def install_skills(self) -> None:
        for skill in sorted(p.parent for p in (self.repo / "skills").glob("*/SKILL.md")):
            for base in (self.home / ".claude" / "skills", self.home / ".agents" / "skills"):
                self.link(base / skill.name, skill, replace_files=False)

    def install_agents(self) -> None:
        for agent in sorted((self.repo / "agents").glob("*.md")):
            self.link(self.home / ".claude" / "agents" / agent.name, agent, replace_files=False)

    def install_rules(self) -> None:
        self.link(self.home / ".codex" / "AGENTS.md", self.repo / "global" / "AGENTS.md")
        self.link(
            self.home / ".claude" / "project-profiles" / "README.md",
            self.repo / "profiles" / "README.md",
        )
        global_dir = self.repo / "global"
        self.write_file(
            self.home / ".claude" / "CLAUDE.md",
            "<!-- Managed by ~/agent-workflow/install.py. Edit the imported files instead. -->\n"
            f"@{global_dir / 'AGENTS.md'}\n@{global_dir / 'CLAUDE.md'}\n",
        )

    def install_hooks(self) -> None:
        path = self.home / ".claude" / "settings.json"
        settings = cast(dict[str, object], json.loads(path.read_text())) if path.exists() else {}
        before = json.dumps(settings, sort_keys=True)
        env = cast(dict[str, str], settings.setdefault("env", {}))
        env.update(ENV)
        hooks = cast(dict[str, list[dict[str, object]]], settings.setdefault("hooks", {}))

        for event in list(hooks):  # drop our previous entries, keep everyone else's
            kept = [group for group in hooks[event] if MARKER not in json.dumps(group)]
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
        for event, matcher, script in HOOKS:
            group: dict[str, object] = {
                "hooks": [{"type": "command", "command": f'"{self.repo / "hooks" / script}"'}]
            }
            if matcher is not None:
                group["matcher"] = matcher
            hooks.setdefault(event, []).append(group)

        if json.dumps(settings, sort_keys=True) == before:
            return
        if path.exists():
            if self._do(f"back up {path} -> {path.name}.bak"):
                shutil.copyfile(path, path.with_name(f"{path.name}.bak"))
        if self._do(f"update hooks and env in {path}"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(settings, indent=2) + "\n")

    def run(self) -> int:
        self.install_skills()
        self.install_agents()
        self.install_rules()
        self.install_hooks()
        for action in self.actions:
            print(("would " if self.dry_run else "") + action)
        if not self.actions:
            print("Everything is already installed.")
        for problem in self.problems:
            print(f"problem: {problem}", file=sys.stderr)
        return 1 if self.problems else 0


def main(argv: list[str]) -> int:
    if argv[1:] not in ([], ["--dry-run"]):
        print(__doc__, file=sys.stderr)
        return 2
    return Installer(home=Path.home(), dry_run=argv[1:] == ["--dry-run"]).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
