## What

A toolset to make agents work more consistently across the entire development lifecycle. I created it because I realized my agents were delivering inconsistent quality across my repos (and even within a repo it fluctuated). It's built on the "leave the code better than you found it" principle. Agents ask questions and define acceptance criteria before building, get an independent review and prove it works before ending the turn. It also contains a self-improvement loop, so a spotted mistake becomes a new rule and a new eval case.

## How a feature gets built

1. `scope-feature` asks you questions until "done" is clear, written as testable acceptance criteria.
2. `design-feature` picks the simplest design and records big decisions as ADRs.
3. `build-feature` builds it test-first, in small slices.
4. `review-change` has fresh reviewers check the code against the standards and the spec.
5. `feature-qa` tries it in the running app.
6. `ship` commits it, but only when you ask.
7. `retro` turns mistakes into new rules or checks, after you approve them.

Bugs go through `fix-bug`: reproduce it first, then fix it. You don't have to name the skills. Describe what you want, and the right one starts.

## Evals

Most of this repo is markdown, so why evals? Because a skill only helps if the agent actually picks it. The agent decides that by reading the skill descriptions, and a small change in wording can make it skip a step. I wanted to know, not guess, whether a request reaches the right skill.

There are 19 cases. Each one runs a real Claude Code session in a throwaway repo and checks which skill it loads first, and that it doesn't touch any code before that. For example, "the invoice total comes out as 15 instead of 1.50, can you look into it?" has to go to `fix-bug`, even though it never says "bug".

The first run passed 16 of 19, and two of the failures were real. Asking "what's going on" about an error got a quick answer instead of the bug workflow, and "review my change" got a review from the same agent instead of independent reviewers. After rewording two skill descriptions, all 19 pass. I rerun them after every change to a skill or rule.

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
