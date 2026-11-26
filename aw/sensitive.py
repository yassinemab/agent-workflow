"""Finds data that must not be published: credentials, personal emails, IP addresses,
home folders with a real user name, and words from a private list.

The private list lives outside the repo (`~/.config/agent-workflow/sensitive-words.txt`,
one word per line, `#` for comments), because listing the words in the repo
would publish them.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

_CREDENTIALS = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{20,}"
    r"|sk-[A-Za-z0-9]{32,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|-----BEGIN" r"[A-Z ]*PRIVATE KEY-----"
    r"|(?i:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ALLOWED_EMAIL = re.compile(r"(?:@example\.(?:com|org|net)|@users\.noreply\.github\.com|^noreply@anthropic\.com)$", re.I)
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_ALLOWED_IP = re.compile(r"^(?:127\.|0\.0\.0\.0$|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)")
_HOME_PATH = re.compile(r"/(?:Users|home)/(?!me/|you/|user/|<)[A-Za-z0-9._-]+/")


@dataclass(frozen=True)
class Finding:
    line: int
    kind: str


def words_path() -> Path:
    override = os.environ.get("AW_SENSITIVE_WORDS")
    return Path(override) if override else Path.home() / ".config" / "agent-workflow" / "sensitive-words.txt"


def load_words(path: Path) -> tuple[str, ...]:
    if not path.is_file():
        return ()
    lines = (line.strip().lower() for line in path.read_text().splitlines())
    return tuple(line for line in lines if line and not line.startswith("#"))


def _is_personal_email(match: re.Match[str], line: str) -> bool:
    if _ALLOWED_EMAIL.search(match.group()):
        return False
    # `\n@pytest.mark.skip` in a string literal is an escape plus a decorator, not an email.
    return not (match.start() > 0 and line[match.start() - 1] == "\\")


def scan_text(text: str, words: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if _CREDENTIALS.search(line):
            findings.append(Finding(number, "credential"))
        if any(_is_personal_email(match, line) for match in _EMAIL.finditer(line)):
            findings.append(Finding(number, "email"))
        if any(not _ALLOWED_IP.match(ip) for ip in _IPV4.findall(line)):
            findings.append(Finding(number, "ip address"))
        if _HOME_PATH.search(line):
            findings.append(Finding(number, "home path"))
        lowered = line.lower()
        if any(word in lowered for word in words):
            findings.append(Finding(number, "private word"))
    return findings
