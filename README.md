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

- **Why:** a skill only helps if the agent picks it, and one wording change can make it skip a step. Evals make that testable.
- **What:** 19 real Claude Code sessions in a throwaway repo. A case passes when the right skill loads first, before any code is touched.
- **Result:** the first run caught two real misses. "What's going on" about an error skipped `fix-bug`, and "review my change" skipped `review-change`. After two rewordings, 19 of 19 pass.

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
