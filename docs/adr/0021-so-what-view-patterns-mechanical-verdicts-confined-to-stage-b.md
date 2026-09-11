# ADR-0021: The so-what view — patterns are mechanical and carry no verdict; a verdict lives only in an evaluated synthesis, and only if it earns its place

**Date:** 2026-09-11 · **Status:** accepted · **Decides:** [issue #16](https://github.com/dempseydata/hindsight/issues/16) (the charting session); map [#18](https://github.com/dempseydata/hindsight/issues/18) · **Touches:** ADR-0006, ADR-0010

## Context

The brief for a fourth view asked the questions that only appear across N sessions of one project: a consumer with poor cost-to-outcome, cost drifting against the project's own baseline, declared process diverging from the run trail, the same correction issued repeatedly, a recurring dead end. It proposed two stages — **A**, mechanical candidate detection over stored data; **B**, a model synthesis over compact digests — and claimed the view could issue "would change X" verdicts because a mechanical gate would let no model-only finding through.

That claim runs into two standing decisions. ADR-0006 dropped the why-view because rationale attribution was unreliable; ADR-0010 gave the how-view no verdicts because the declared process is conditional and a checker false-positives, so comparison is juxtaposition and judgement stays with the operator. A mechanical gate does not answer either: it proves a finding is *grounded* — a candidate exists in the data — not that the verdict drawn from it is *right*. "This MCP server has a 40% error share and cost 12% of the window" is a fact; "drop it" is a judgement, and the gate says nothing about the judgement.

## Decision

- **Stage A emits patterns, and a pattern carries no verdict.** A pattern is a cross-session fact stated with its numbers against the project's own baseline — the juxtaposition rule of ADR-0010 extended across sessions. It recommends nothing. The operator judges, as in the how-view.
- **A verdict lives only in Stage B, and Stage B is conditional.** Before any Stage B is designed, a design-time eval over real project-windows decides whether a model synthesis adds anything over the ranked pattern list, against a criterion fixed before the run. If it does not, Stage A ships alone and this clause resolves as "not built". If it does, Stage B is load-bearing model output under the full Evaluation discipline (frozen set, threshold before the prompt, regression on every prompt or model change, stored and gated like the status narrative — ADR-0012), and every finding traces to at least one pattern.
- **Stage A v1 is the three signals plain SQL can already state**: low-yield consumer (tool events' per-call error flag and the message-lens token join), cost trend against the project's own baseline, declared/actual drift from the how-view's off-script aggregate. The two model-dependent signals — repeated correction, recurring dead end — enter only if a prototype over real data proves a mechanical definition holds; a kill criterion is written before either runs. Acceptance rate is not a signal: OTEL edit decisions on this machine are 16,771 accept to 4 reject.
- **The reversal of ADR-0006/0010 is therefore confined to Stage B and conditional on its eval.** Nothing mechanical in the product issues a verdict; that rule stands.

## Considered options

- **Verdicts from Stage A, gated mechanically (the brief as written).** Rejected: the gate grounds the finding without validating the verdict, so it reopens ADR-0010's objection unanswered.
- **No verdicts anywhere; drop Stage B.** Cheapest and free of Evaluation burden, but decides against the "so what" without ever measuring whether a synthesis helps. The conditional keeps the question open at the cost of one eval.
- **All five signals in v1.** Commits to two definitions that do not exist yet; the corrective-turn signal is a second model pass with its own eval before Stage B's go/no-go is even known.

## Consequences

- CONTEXT.md gains *so-what view*, *pattern*, *finding*. The brief's "candidate" is a pattern — one term.
- Map #18 charts the route: the Stage A prototype first, then window/baseline, evidence, compute placement, the Stage B criterion, its dry run, and the greybox. Building the view is a separate effort after `to-spec`.
- The view compares a project against its own baseline only; cross-project comparison is out of scope.
- No new ingest path, no raw JSONL to a model, read-only view, the analysis run the only writer, the Haiku pin unchanged — the brief's scope guards hold.
