from __future__ import annotations

import re
import unittest

from aw.config import BlockedCommand
from aw.guards import check_command


def on_branch(name: str | None):
    return lambda _path: name


class DestructiveGitCommandsAreDenied(unittest.TestCase):
    def assert_denied(self, command: str, branch: str | None = "feature") -> None:
        verdict = check_command(command, on_branch(branch))
        self.assertFalse(verdict.allowed, command)
        self.assertIn("ask them to run it themselves", verdict.reason)

    def assert_allowed(self, command: str, branch: str | None = "feature") -> None:
        self.assertTrue(check_command(command, on_branch(branch)).allowed, command)

    def test_force_push_in_every_spelling(self) -> None:
        for command in (
            "git push --force",
            "git push -f origin feature",
            "git push --force-with-lease",
            "git push -uf origin feature",
            "git push origin +feature",
            "git push --mirror",
        ):
            self.assert_denied(command)

    def test_deleting_a_remote_branch(self) -> None:
        self.assert_denied("git push origin --delete old")
        self.assert_denied("git push origin :old")

    def test_push_to_main_or_master(self) -> None:
        self.assert_denied("git push origin main")
        self.assert_denied("git push origin HEAD:main")
        self.assert_denied("git push origin feature:refs/heads/master")
        self.assert_denied("git push --all")

    def test_bare_push_depends_on_current_branch(self) -> None:
        self.assert_denied("git push", branch="main")
        self.assert_denied("git push origin", branch="master")
        self.assert_denied("git push origin HEAD", branch="main")
        self.assert_allowed("git push", branch="feature")
        self.assert_allowed("git push -u origin feature", branch="feature")

    def test_push_with_dash_c_uses_that_repos_branch(self) -> None:
        def branch_of(path: str | None) -> str | None:
            return "main" if path == "../other" else "feature"

        self.assertFalse(check_command("git -C ../other push", branch_of).allowed)
        self.assertTrue(check_command("git push", branch_of).allowed)

    def test_reset_hard_but_not_soft(self) -> None:
        self.assert_denied("git reset --hard HEAD~1")
        self.assert_allowed("git reset --soft HEAD~1")
        self.assert_allowed("git reset HEAD file.py")

    def test_stash_except_reading_it(self) -> None:
        self.assert_denied("git stash")
        self.assert_denied("git stash push -m wip")
        self.assert_denied("git stash pop")
        self.assert_allowed("git stash list")
        self.assert_allowed("git stash show -p")

    def test_restoring_files(self) -> None:
        self.assert_denied("git checkout -- app.py")
        self.assert_denied("git checkout .")
        self.assert_denied("git checkout main -- app.py")
        self.assert_denied("git restore app.py")
        self.assert_denied("git restore --staged --worktree app.py")
        self.assert_allowed("git restore --staged app.py")
        self.assert_allowed("git checkout -b new-feature")

    def test_clean_force_but_not_dry_run(self) -> None:
        self.assert_denied("git clean -fd")
        self.assert_denied("git clean -xdf")
        self.assert_allowed("git clean -n")
        self.assert_allowed("git clean -nd")

    def test_switch_discarding_changes(self) -> None:
        self.assert_denied("git switch --discard-changes main")
        self.assert_allowed("git switch -c feature")

    def test_commands_hidden_in_chains_wrappers_and_subshells(self) -> None:
        self.assert_denied("cd repo && git stash")
        self.assert_denied("git status; git reset --hard")
        self.assert_denied("GIT_TRACE=1 git push --force")
        self.assert_denied("sudo git clean -f")
        self.assert_denied("bash -c 'git stash'")
        self.assert_denied("git -C ../repo -c core.pager=cat stash")
        self.assert_denied("git status\ngit stash")

    def test_harmless_commands_pass(self) -> None:
        for command in (
            "git status",
            "git log --oneline -5",
            "git diff HEAD",
            "git commit -m 'stash the --force flag in docs'",
            "echo git stash",
            "ls -la",
        ):
            self.assert_allowed(command)

    def test_unbalanced_quotes_still_get_checked(self) -> None:
        self.assert_denied("git stash push -m \"wip")


class ProjectBlockedCommands(unittest.TestCase):
    rules = (BlockedCommand(re.compile(r"\bmysqldump\b"), "It locks every table."),)

    def test_matching_command_is_denied_with_the_project_reason(self) -> None:
        verdict = check_command("ssh prod 'mysqldump db | grep x'", on_branch("main"), self.rules)
        self.assertFalse(verdict.allowed)
        self.assertIn("It locks every table.", verdict.reason)

    def test_other_commands_pass(self) -> None:
        self.assertTrue(check_command("mysql -e 'select 1'", on_branch("main"), self.rules).allowed)


if __name__ == "__main__":
    unittest.main()
