# agent-workflow

One place for how coding agents (Claude Code and Codex) work on this machine: the global rules, the lifecycle skills, the subagents, and the hooks that enforce the rules that must never be broken.

## Layout

| Path | What | Installed as |
|---|---|---|
| `global/AGENTS.md` | Global rules for every agent and repo | `~/.codex/AGENTS.md` (link); imported by `~/.claude/CLAUDE.md` |
| `global/CLAUDE.md` | Claude Code-only additions | imported by `~/.claude/CLAUDE.md` |
| `skills/<name>/` | One skill per lifecycle stage, plus helpers | `~/.claude/skills/<name>`, `~/.agents/skills/<name>` (links) |
| `agents/<name>.md` | Claude Code subagents: `standards-reviewer`, `spec-reviewer`, `verifier` | `~/.claude/agents/<name>.md` (links) |
| `hooks/` | Claude Code hooks (Python, stdlib only) | registered in `~/.claude/settings.json` |
| `bin/run-checks` | Runs a project's full checks from its `workflow.json` and records the result | run as `~/agent-workflow/bin/run-checks` |
| `bin/run-evals`, `evals/` | Checks that prompts reach the right skill, in headless Claude sessions on a throwaway fixture repo | run by hand after skill or rule changes |
| `aw/` | Shared, typed core the hooks and scripts import | — |
| `profiles/README.md` | How project profiles and `workflow.json` work | `~/.claude/project-profiles/README.md` (link) |
| `tests/` | Tests for the hooks, `run-checks` and the installer | — |

## Lifecycle

`scope-feature` → `design-feature` (+ `adr`) → `build-feature` → `review-change` → `feature-qa` / `check-design` → `ship` → `retro`. Bugs go through `fix-bug`; behavior-preserving cleanups through `refine-code`. The table in `global/AGENTS.md` §1 is the authoritative version.

## Hooks

| Hook | Event | What it does |
|---|---|---|
| `guard_commands.py` | PreToolUse (Bash) | Denies force-push, push to main/master, `reset --hard`, `stash`, file restores, `clean -f`, and the project's `blocked_commands` |
| `guard_rule_files.py` | PreToolUse (Edit, Write, MultiEdit, NotebookEdit, Bash) | Shows a confirmation prompt before writes to `~/agent-workflow`, `~/.claude/CLAUDE.md` or `~/.claude/settings*.json`. In bypass-permissions mode Claude Code shows no prompts, so the user's yes in chat is the gate |
| `guard_subagent_model.py` | PreToolUse (Agent) | Denies subagents on `opus`/`fable` and forks; the installer also sets `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` |
| `flag_test_edits.py` | PostToolUse (Edit, Write, MultiEdit) | Warns the agent when an edit removes assertions from a test or adds a skip |
| `track_turn.py` | UserPromptSubmit | Starts a new turn: forgets the previous turn's edits |
| `track_edits.py` | PreToolUse (Edit, Write, MultiEdit, NotebookEdit) | Records which file this session is about to edit, and its repo's state before the first edit of the turn |
| `require_checks.py` | Stop | Blocks ending a turn while files this session edited, in any repo, haven't been checked by `run-checks` as they are now. Other sessions' changes don't count; Bash edits aren't tracked |

These are a safety net over shell text and edit content, not a sandbox: a determined workaround (a script that runs git) gets past them. The three guards deny the call when they crash, so a bug can't switch protection off; the other hooks report the error and let the session continue. Every decision is logged to `~/.cache/agent-workflow/events.jsonl`, which `retro` reads. Codex doesn't run these hooks; it relies on the rules alone.

## Evals

```bash
~/agent-workflow/bin/run-evals                 # all cases
~/agent-workflow/bin/run-evals --case review   # one case; --repeat 2 to check flakiness
```

Each case in `evals/cases.json` runs `claude -p` in a throwaway copy of `evals/fixture/`, in `dontAsk` permission mode, and passes when the first skill it loads is the expected one, with no code edits before it. A run stops as soon as the verdict is known. The runs use your Claude subscription (about 19 short sessions), so they aren't part of `run-checks`. Run them after changing a skill description or a rule, and add a case whenever a request reached the wrong skill. Results are saved in `~/.cache/agent-workflow/evals/`.

## Install and update

```bash
python3 ~/agent-workflow/install.py --dry-run   # show what would change
python3 ~/agent-workflow/install.py             # link everything; safe to run again
```

The installer backs up any file it replaces (`*.bak-<timestamp>`) and never replaces a real skill folder. Move such a folder into `skills/` first.

## Changing the workflow

Edit files here, not through the links (Claude Code's Edit tool refuses to write through them). Then run the checks:

```bash
cd ~/agent-workflow && bin/run-checks
```

Changes to the workflow follow the self-improvement rule in `global/AGENTS.md` §11: an agent proposes the exact change at the end of a turn, and makes it only after your explicit yes in chat. Then it runs `bin/run-checks`, and `bin/run-evals` if a skill or rule changed.
