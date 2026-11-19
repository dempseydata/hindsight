# ADR-0032: Process resolution — a root `local-process.md` deviates from the house master; the master declares every house layout

**Date:** 2026-11-13 · **Status:** accepted, amended by issue #98 (Consequences) · **Amends:** ADR-0011 (container) · **Decides:** issue #63 (map #59, v2 audit core)

## Context

ADR-0011 put the process declaration at line 1 of `<project-root>/.claude/my-process.md`, as the only location read. Two things have changed since then. The house process now has a master, `my-standards/my-process.md` in the workspace, and `~/.claude/CLAUDE.md` names it under `## Process` as the default for any software-dev project. Every product also carries a duplicate of the master, and in practice its frontmatter only restates the master's or differs from it in a few paths. While charting map #59 we settled that a project's process is the house master unless a root `local-process.md` says otherwise, that `none` means no process, and that today's declaration buckets all history. This ADR fixes what charting left open: the file's format, how the master is found, and how one master's path markers serve the three house layouts (private `ideation/`, born-public `background/ideation/`, plugin `docs/ideation/`).

The workspace as of 2026-11-13: one project already holds a `local-process.md` reading `none`; four projects declare frontmatter in `.claude/my-process.md`, one of them identical to the master's private-layout default and three of them deviating from it in their paths or stages.

## Decision

**Resolution order, one winner.** If `<project-root>/local-process.md` exists, it decides. Otherwise the house master's frontmatter applies. v2 never reads `.claude/my-process.md`. Reading two locations would need a precedence rule, and the winner would be invisible to the operator.

**`local-process.md` format.** The whole file, trimmed, is either `none` (no process: the project has no how-view) or an ADR-0011 frontmatter fence at line 1, with free prose allowed below the fence. The fence is parsed by ADR-0011's grammar, unchanged. Anything else is *invalid* and shown loudly, an empty file included: a malformed file must never read as an opt-out.

**Finding the master.** Read `~/.claude/CLAUDE.md`, take the first backticked token ending in `my-process.md` under the `## Process` heading, and expand `~`. CLAUDE.md already holds the pointer, so a move of the master costs one edit there and none in hindsight.

**Master unresolvable is invalid, never absent.** This covers a missing heading or pointer, a missing or unreadable master file, and an invalid fence in the master. The project then gets the *invalid* state, with a one-liner naming the master's path and the reason. A master that has gone missing must not look like a deliberate `none`.

**The master declares every house layout.** Its path markers list all three template layouts explicitly, for example `paths: [ideation/, background/ideation/, docs/ideation/, definition/, background/definition/, docs/definition/]`. A path that doesn't exist in a project never matches. ADR-0011's anchored, whole-segment matching is unchanged.

**Provenance is shown.** The how-view states which source resolved the declaration, "house master" with its path or `local-process.md`, in one line beside the stated-process panel.

## Considered options

- **Keep reading `.claude/my-process.md`, as ADR-0011 does.** That location is `@`-included into every session (a token tax on each), and it is untracked in born-public repos. It also repeats the master's frontmatter in every product.
- **Read both locations with a precedence rule.** That is two places to look and a silent winner.
- **Find the master through a fixed default path with an environment-variable override, or a hindsight config file.** Either would be a second source of truth beside the pointer CLAUDE.md already carries.
- **Match path markers at any depth** (`ideation/` also matches `background/ideation/`). This quietly widens matching for every project and every marker, to solve a problem that three more list entries solve.
- **A `local-process.md` in every born-public project.** That is the per-project cost this decision exists to remove.
- **Treat an unresolvable master as absent.** Unknown would then read as zero.

## Consequences

- When this is built, the frontmatter is deleted from every `.claude/my-process.md` copy. The master's frontmatter stops being "the private-layout default" and becomes the house declaration for all layouts, and its sync note changes to match.
- Projects whose declaration differs from the master move it to a root `local-process.md`. These are three of the four declaring projects, plus hindsight for `eval/` under Build and the plugin layout's `skills/` and `cli/` unless the master takes them.
  *Amended 2026-11-19 (issue #98):* the master took them. Its frontmatter lists `background/ideation/`, `background/definition/`, `background/design/`, `cli/`, `skills/` and `eval/`, so hindsight resolves from the house master, and the draft `local-process.md` from #94 was dropped (2304326). A `local-process.md` exists only to replace the house process for its project alone. It is never a copy of the master, and never a patch to the master's paths: a missing house layout path is added to the master. That hindsight's own paths stage under the master is not tested: the master lives outside the repo, and tests pin the user-level CLAUDE.md away.
- Every project without a local file gets the master, non-dev folders included. A folder that should have no how-view needs `none` written, or its view will be all off-script.
- The declaration states of ADR-0011 stand. *Absent* now means `none`. *Invalid* also covers an unresolvable master.
