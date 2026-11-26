# agent-workflow

Rules, skills and hooks that make AI coding agents (Claude Code and Codex) work like a careful senior developer: ask questions before building, write tests first, get an independent review, and prove it works before saying "done".

## Why

AI agents are fast, but they make the same mistakes over and over: they duplicate code, over-engineer, weaken tests until they pass, and say "it works" without checking. Rules in a prompt help, but agents forget them. This repo pairs clear rules with a skill for each step and hooks that enforce the rules that must never be broken.

## How a feature gets built

1. `scope-feature` asks you questions until "done" is clear, written as testable acceptance criteria.
2. `design-feature` picks the simplest design and records big decisions as ADRs.
3. `build-feature` builds it test-first, in small slices.
4. `review-change` has fresh reviewers check the code against the standards and the spec.
5. `feature-qa` tries it in the running app.
6. `ship` commits it, but only when you ask.
7. `retro` turns mistakes into new rules or checks, after you approve them.

Bugs go through `fix-bug`: reproduce it first, then fix it. You don't have to name the skills. Describe what you want, and the right one starts.

## What's inside

- `global/`: the rules every agent follows
- `skills/`: one skill per step above, plus a few helpers
- `agents/`: read-only reviewer and verifier agents
- `hooks/`: block dangerous commands (force push, `git reset --hard`, pushing to `main`), warn when a test gets weaker, and keep a turn from ending until the tests have run
- `evals/`: checks that requests reach the right skill (19 of 19 pass)

## Install

You need Python 3.10+, git and Claude Code. Tested on macOS.

```bash
git clone https://github.com/yassinemab/agent-workflow ~/agent-workflow
python3 ~/agent-workflow/install.py --dry-run   # see what it will change
python3 ~/agent-workflow/install.py
```

It has to live in `~/agent-workflow`. The installer links the rules and skills into `~/.claude` (and `~/.agents` for Codex) and adds the hooks to `~/.claude/settings.json`. It backs up anything it replaces.

To let the hooks run a project's tests, give that project a `workflow.json` (see `profiles/README.md`).

## Good to know

- The hooks are a safety net, not a sandbox.
- They run on your machine on every tool call, so read changes to `hooks/` before you pull them.
- Codex follows the rules and skills, but doesn't run the hooks.
- `bin/run-evals` runs real Claude sessions, so it uses your subscription.

## Credits

Ideas from [mattpocock/skills](https://github.com/mattpocock/skills) and Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack). `skills/check-design` paraphrases six public design skills, listed in its checklist. `skills/unslop` is adapted from [blader/humanizer](https://github.com/blader/humanizer) (MIT).

## License

MIT, see `LICENSE`.
