from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from aw.sensitive import scan_text

ROOT = Path(__file__).resolve().parent.parent
# Fake secrets are built from pieces so this file doesn't trip the scanner itself.
FAKE_ANTHROPIC_KEY = "sk-" + "ant-" + "a1B2" * 8
FAKE_GITHUB_TOKEN = "gh" + "p_" + "x9Y8" * 9
FAKE_AWS_KEY = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
PRIVATE_KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY-----"


def kinds(text: str, words: tuple[str, ...] = ()) -> list[str]:
    return [finding.kind for finding in scan_text(text, words)]


class FindsSensitiveData(unittest.TestCase):
    def test_credentials(self) -> None:
        self.assertEqual(kinds(f"key = {FAKE_ANTHROPIC_KEY}"), ["credential"])
        self.assertEqual(kinds(f"token: {FAKE_GITHUB_TOKEN}"), ["credential"])
        self.assertEqual(kinds(FAKE_AWS_KEY), ["credential"])
        self.assertEqual(kinds(PRIVATE_KEY_HEADER), ["credential"])
        self.assertEqual(kinds("password = " + '"hunter2' + 'hunter2"'), ["credential"])

    def test_personal_emails_but_not_placeholders(self) -> None:
        self.assertEqual(kinds("contact jane.doe@" + "gmail.com"), ["email"])
        self.assertEqual(kinds("content = 'import x\\n@pytest.mark.skip'"), [])  # an escape, not an email
        for allowed in ("test@example.com", "1+me@users.noreply.github.com", "noreply@anthropic.com"):
            self.assertEqual(kinds(allowed), [], allowed)

    def test_ip_addresses_but_not_local_or_documentation_ones(self) -> None:
        self.assertEqual(kinds("ssh root at 10.20." + "30.40"), ["ip address"])
        for allowed in ("127.0.0.1", "0.0.0.0", "192.0.2.10", "198.51.100.7", "203.0.113.9"):
            self.assertEqual(kinds(allowed), [], allowed)

    def test_home_folders_with_a_real_user_name(self) -> None:
        self.assertEqual(kinds("open /Users/" + "alice/projects/x"), ["home path"])
        self.assertEqual(kinds("cd /home/" + "bob/app"), ["home path"])
        self.assertEqual(kinds("dd of=/Users/me/agent-workflow/x"), [])

    def test_words_from_the_private_list_case_insensitively(self) -> None:
        self.assertEqual(kinds("Deployed to the ACME cluster", ("acme",)), ["private word"])
        self.assertEqual(kinds("nothing here", ("acme",)), [])

    def test_line_numbers_are_reported(self) -> None:
        findings = scan_text("fine\nemail jane@" + "gmail.com\n", ())
        self.assertEqual([(f.line, f.kind) for f in findings], [(2, "email")])


class ScanCommand(unittest.TestCase):
    def test_scans_what_git_would_commit_and_skips_ignored_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / ".gitignore").write_text("secret.log\n")
            (repo / "clean.md").write_text("all good\n")
            (repo / "leak.py").write_text(f"KEY = '{FAKE_ANTHROPIC_KEY}'\n")
            (repo / "secret.log").write_text(f"{FAKE_ANTHROPIC_KEY}\n")
            (repo / "notes.md").write_text("Our client Globex wants this\n")
            words = Path(tmp) / "words.txt"
            words.write_text("# private words, one per line\nglobex\n")
            env = {**os.environ, "AW_SENSITIVE_WORDS": str(words)}
            result = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "scan-sensitive")],
                cwd=repo, capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("leak.py:1: credential", result.stdout)
            self.assertIn("notes.md:1: private word", result.stdout)
            self.assertNotIn("secret.log", result.stdout)
            self.assertNotIn("clean.md", result.stdout)
            self.assertNotIn(FAKE_ANTHROPIC_KEY, result.stdout)  # findings never echo the secret

            (repo / "leak.py").write_text("KEY = load_from_env()\n")
            (repo / "notes.md").write_text("A client wants this\n")
            clean = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "scan-sensitive")],
                cwd=repo, capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(clean.returncode, 0, clean.stdout)


if __name__ == "__main__":
    unittest.main()
