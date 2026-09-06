# Why Hindsight was built

The README says what the product is. This is the record: why it exists, who it is for, how it was built, and what was reversed along the way.

## The problem

I run a skill- and MCP-heavy Claude Code setup across many independent projects, and I evolve that setup constantly. Three questions about my own usage were unanswerable from anything on disk: where did my tokens go (cache economics, the sunk session-start cost each project pays, per-skill and per-MCP usage); what did I actually do (an audit of actions and decisions per session, reviewable months later); and how did the process actually run against what was declared. Hindsight answers them from local history alone.

The demand is one user — me — and that is stated rather than hidden. The bar for a personal tool is acted-upon insights, not interest. A previous incarnation, limited in functionality and in retrospect a learning exercise, cleared that bar: its findings drove a real skills cleanup and a full project restructure. Both of those acted-upon insights were setup-evolution events, which argued for centring this product on the audit trail rather than the token dashboard — token reporting is steadily commoditised by first-party tooling, while only a local tool over full history can reconstruct decisions across months.

The six forcing questions that tested the premise, and their answers, are in [ideation/framing.md](ideation/framing.md). The definition that came out of them is in [definition/](definition/), together with the red-team pass that attacked it.

## Who reads this repo

Answered late, and that is itself part of the record. The product was built in a private working repo whose history carried real session-derived data — fixtures drawn from my own transcripts, quoted transcript text in issue bodies, screenshots of live views — and publication was first attempted as a flip of that repo to public. It took a multi-session sanitisation attempt to establish that git history is append-only and a flip publishes everything ever committed, so the application was exported instead ([tickets 087](tickets/087-publication-pre-flight.md) and [088](tickets/088-flip-public-retire-predecessors.md)).

This repo is the successor to that export, and it is public by design: the working record — these background documents, the [tickets](tickets/), the [decision records](../docs/adr/) — is part of what is published, written knowing that. What never enters it: session-derived data (`local-data/` is ignored), fixtures drawn from it, unfiltered screenshots, secrets, and machine paths — a pre-commit hook refuses the last two by pattern.

The lesson is now house policy: decide the audience at ideation, not at ship.

## How it was built

The build carried a second, stated purpose: an end-to-end evaluation of the process and toolchain it was built with. It ran in phases — ideation → definition → design → build — governed by a per-project process declaration ([.claude/my-process.md](../.claude/my-process.md)) that the tooling itself reads: the how-view is hindsight rendering its own declared process against its own trail.

- **Ideate.** Six forcing questions against the premise before any divergence ([ideation/framing.md](ideation/framing.md)), then an eval gate before commitment: a cheap-model run over real transcript days ([ideation/eval-why-extractability/](ideation/eval-why-extractability/)) that confirmed the wedge and falsified an assumption — model-quoted evidence failed verbatim verification, so evidence is attached mechanically and model-quoted text is never stored as evidence ([ADR-0002](../docs/adr/0002-extraction-contract.md)).
- **Define.** [definition.md](definition/definition.md), then [red-teamed](definition/red-team.md) with the load-bearing claims tested rather than argued ([red-team-tests.md](definition/red-team-tests.md)); the ingest schemas were verified against real payloads before anything was built on them ([ingest-schema-verification.md](definition/ingest-schema-verification.md)).
- **Design.** Prototype-first for a dense tool UI: greybox screens on real data settled the information architecture before any styling, then five candidate directions were diverged and narrowed comparatively — three variants of the winner, identical real content in every comp — into the indigo deck recorded in [ADR-0007](../docs/adr/0007-direction-indigo-deck.md), with [design/tokens.css](../design/tokens.css) as the single styling contract. The inputs that fed that choice are in [design/design-inputs.md](design/design-inputs.md); what was handed to the build is in [design/build-handoff.md](design/build-handoff.md); the taste research behind it is in [research/taste-references.md](research/taste-references.md).
- **Build.** A map of tracer-bullet tickets, one per session, each interrogated up front, built red-green, and reviewed before commit. All 88 are in [tickets/](tickets/), exported from the private working repo's issue tracker with their closing comments. Vocabulary lives in [CONTEXT.md](../CONTEXT.md); every decision with teeth is an ADR in [docs/adr/](../docs/adr/).
- **Evaluation as a recurring discipline, not a stage.** Wherever model output is load-bearing: a frozen eval set drawn from real data ([eval/](../eval/)), a numeric threshold decided in advance, and a regression run on any prompt change.

## Reversals, told plainly

The record is the point.

- **The why-view was dropped wholesale** ([ADR-0006](../docs/adr/0006-v1-scope-two-views.md)). The product was framed as three views; putting real pages side by side showed the why-view's prose near-duplicated the what ledger while carrying almost the entire standing eval burden. The clean cut won over a merge. A different third view — *how* — was decided for post-v1 ([ADR-0010](../docs/adr/0010-how-view-mechanical-trail-declared-stages.md)) and shipped.
- **28 sessions retried forever** ([ADR-0015](../docs/adr/0015-lost-sessions-terminal-status.md)). Transcripts aged past Claude Code's retention while sessions waited behind a rate-limit pause, and the queue had no state meaning *unknowable*. The fix was a terminal `lost` status decided by an existence test, greedy extraction ahead of the model loop so the race cannot recur, and honest ledger rows — *transcript pruned before analysis, unrecoverable* — instead of silence.
- **Day buckets were UTC** ([ADR-0014](../docs/adr/0014-local-day-buckets.md)). 11.5% of usage rows landed on the wrong day for an operator whose evenings straddle midnight UTC. Timestamps stay as the CLI wrote them; the day is derived at read time in the host's zone. Making the zone configurable is the first ticket on this repo.
- **Publication was a flip, then an export, then this** — see *Who reads this repo* above.
