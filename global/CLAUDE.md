# Claude Code additions

These add to the global rules in `AGENTS.md` (imported above) for Claude Code only.

- **Skills** live in `~/agent-workflow/skills/` and are linked into `~/.claude/skills/`. Edit them in `~/agent-workflow`; the Edit and Write tools refuse to write through links.
- **Questions:** when a skill drills the user, use `AskUserQuestion` for questions with clear options (recommended option first, marked "(Recommended)"). Ask open questions in prose.
- **Subagents** (`~/.claude/agents/`, linked from `~/agent-workflow/agents/`), all on `sonnet`:
  - `standards-reviewer`: reviews a change against the principles and failure patterns. Read-only.
  - `spec-reviewer`: reviews a change against the spec's acceptance criteria and flags scope creep. Read-only.
  - `verifier`: runs the checks and the acceptance-criteria checks, then reports pass or fail with evidence. It does not edit code.

  Never let the agent that wrote the code give the final verdict on it. When you spawn any other subagent, pass `model: "sonnet"`, or `"haiku"` for plain search. Subagents without a model get `sonnet` from `CLAUDE_CODE_SUBAGENT_MODEL`.
- **Hooks** (`~/agent-workflow/hooks/`, registered in `~/.claude/settings.json`):
  - `guard-commands`: blocks force-push, `reset --hard`, `git stash`, file restores, `git clean -f`, pushes to `main`/`master`, and project-specific commands from the project's `workflow.json`.
  - `guard-rule-files`: shows a confirmation prompt before writes to `~/agent-workflow`, `~/.claude/CLAUDE.md` or `~/.claude/settings*.json`. Claude Code shows no prompts in bypass-permissions mode, so there the user's explicit yes in chat is the only gate (`AGENTS.md` §11).
  - `guard-subagent-model`: blocks subagents on `opus` or `fable`, and forks, which always run on the main model.
  - `flag-test-edits`: warns when an edit removes assertions from a test or adds a skip.

  The guards deny the call if they crash. Every hook decision is logged to `~/.cache/agent-workflow/events.jsonl`. When a hook blocks you, follow its message. Don't work around it.
- **Plan mode:** present an approved spec or design with `ExitPlanMode`.
