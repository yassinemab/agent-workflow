from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from aw.repo import tree_hash


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


class TreeHash(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "app.py").write_text("x = 1\n")
        # An old timestamp, so git's index treats its cached stat data as trustworthy.
        old = (self.repo / "app.py").stat().st_mtime - 100
        os.utime(self.repo / "app.py", (old, old))
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "init")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_sees_a_same_size_edit_even_when_the_timestamp_is_unchanged(self) -> None:
        before = tree_hash(self.repo)
        path = self.repo / "app.py"
        stat = path.stat()
        path.write_text("x = 2\n")
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertNotEqual(tree_hash(self.repo), before)

    def test_includes_untracked_files_and_skips_ignored_ones(self) -> None:
        before = tree_hash(self.repo)
        (self.repo / ".gitignore").write_text("*.log\n")
        with_ignore_file = tree_hash(self.repo)
        self.assertNotEqual(with_ignore_file, before)
        (self.repo / "debug.log").write_text("noise\n")
        self.assertEqual(tree_hash(self.repo), with_ignore_file)
        (self.repo / "new.py").write_text("y = 1\n")
        self.assertNotEqual(tree_hash(self.repo), with_ignore_file)

    def test_leaves_the_real_index_alone(self) -> None:
        (self.repo / "new.py").write_text("y = 1\n")
        tree_hash(self.repo)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(status.stdout, "?? new.py\n")


if __name__ == "__main__":
    unittest.main()
