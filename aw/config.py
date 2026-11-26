"""Loading a project's `workflow.json` (format: `profiles/README.md`)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from aw.repo import repo_name

DEFAULT_NO_CHECKS_NEEDED_FOR: tuple[str, ...] = ("*.md", "**/*.md", "docs/**")
DEFAULT_TIMEOUT_MINUTES = 20


class ConfigError(ValueError):
    """workflow.json exists but is invalid."""


@dataclass(frozen=True)
class Check:
    name: str
    cwd: str
    run: str
    timeout_minutes: float = DEFAULT_TIMEOUT_MINUTES


@dataclass(frozen=True)
class BlockedCommand:
    pattern: re.Pattern[str]
    reason: str


@dataclass(frozen=True)
class WorkflowConfig:
    source: Path | None
    checks: tuple[Check, ...]
    no_checks_needed_for: tuple[str, ...]
    blocked_commands: tuple[BlockedCommand, ...]


EMPTY_CONFIG = WorkflowConfig(
    source=None,
    checks=(),
    no_checks_needed_for=DEFAULT_NO_CHECKS_NEEDED_FOR,
    blocked_commands=(),
)


def profiles_dir() -> Path:
    override = os.environ.get("AW_PROFILES_DIR")
    return Path(override) if override else Path.home() / ".claude" / "project-profiles"


def config_path(root: Path) -> Path | None:
    """The first existing workflow.json: the repo's own, then the personal profile's."""
    candidates = [
        root / ".claude" / "workflow.json",
        profiles_dir() / repo_name(root) / "workflow.json",
    ]
    return next((path for path in candidates if path.is_file()), None)


def load_config(root: Path) -> WorkflowConfig:
    path = config_path(root)
    if path is None:
        return EMPTY_CONFIG
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise ConfigError(f"{path}: invalid JSON: {error}") from error
    return parse_config(raw, path)


def parse_config(raw: object, source: Path) -> WorkflowConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"{source}: the top level must be an object")
    data = cast(dict[str, object], raw)
    unknown = set(data) - {"checks", "no_checks_needed_for", "blocked_commands"}
    if unknown:
        raise ConfigError(f"{source}: unknown keys: {', '.join(sorted(unknown))}")
    return WorkflowConfig(
        source=source,
        checks=tuple(_parse_check(item, source) for item in _list(data, "checks", source)),
        no_checks_needed_for=tuple(
            _str(item, "no_checks_needed_for", source)
            for item in _list(data, "no_checks_needed_for", source, DEFAULT_NO_CHECKS_NEEDED_FOR)
        ),
        blocked_commands=tuple(
            _parse_blocked(item, source) for item in _list(data, "blocked_commands", source)
        ),
    )


def _list(
    data: dict[str, object], key: str, source: Path, default: tuple[str, ...] = ()
) -> list[object]:
    value = data.get(key, list(default))
    if not isinstance(value, list):
        raise ConfigError(f"{source}: `{key}` must be a list")
    return cast(list[object], value)


def _str(value: object, where: str, source: Path) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{source}: `{where}` must be a non-empty string")
    return value


def _object(value: object, where: str, source: Path) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigError(f"{source}: every item in `{where}` must be an object")
    return cast(dict[str, object], value)


def _parse_check(item: object, source: Path) -> Check:
    data = _object(item, "checks", source)
    timeout = data.get("timeout_minutes", DEFAULT_TIMEOUT_MINUTES)
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise ConfigError(f"{source}: `checks[].timeout_minutes` must be a positive number of minutes")
    return Check(
        name=_str(data.get("name"), "checks[].name", source),
        cwd=_str(data.get("cwd", "."), "checks[].cwd", source),
        run=_str(data.get("run"), "checks[].run", source),
        timeout_minutes=float(timeout),
    )


def _parse_blocked(item: object, source: Path) -> BlockedCommand:
    data = _object(item, "blocked_commands", source)
    pattern = _str(data.get("pattern"), "blocked_commands[].pattern", source)
    try:
        compiled = re.compile(pattern)
    except re.error as error:
        raise ConfigError(f"{source}: invalid pattern {pattern!r}: {error}") from error
    return BlockedCommand(
        pattern=compiled,
        reason=_str(data.get("reason"), "blocked_commands[].reason", source),
    )
