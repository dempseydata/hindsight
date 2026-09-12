# ADR-0025: Stage B's go/no-go — criterion, model, digest and blind rating fixed before the dry run

**Date:** 2026-09-12 · **Status:** proposed — accepted with #27's verdict, whichever way it falls · **Decides:** [issue #26](https://github.com/dempseydata/hindsight/issues/26); map [#18](https://github.com/dempseydata/hindsight/issues/18) · **Touches:** ADR-0021, ADR-0022, ADR-0023, ADR-0024, ADR-0012

## Context

ADR-0021 made Stage B conditional: a design-time eval over real project-windows decides whether a model synthesis adds anything over the ranked pattern list, *against a criterion fixed before the run*. This ADR is that fixing. It is committed before the dry run ([#27](https://github.com/dempseydata/hindsight/issues/27)) so that git, not memory, proves the order; nothing here moves after #27's numbers exist.

Facts the decision rests on, read from `local-data/` on 2026-09-12 (never committed):

- **Windows exist.** At 14 days, twelve project-windows clear ADR-0022's sparsity floor and carry at least one pattern under the prototype's floors: hindsight-old ×4, career-ops ×4, content ×2, hindsight-new ×1, thisisme ×1. Three windows are controls — thisisme@2026-09-11 is empty (*too thin*), thisisme@2026-07-31 has activity and nothing above the floor (*nothing to report*), content@2026-08-28 has two sessions over two days (*too thin*). Five pattern windows plus two controls leaves seven pattern windows in reserve for a frozen eval set if Stage B goes.
- **A window's typed turns fit one call.** Distinct typed user turns per (session, text) — the universe #21 defined — run 80–190 per active window, 6–18k characters. Every session in the candidate windows has an audit; titles average 64 characters, so the largest window's titles are about 3k characters. The whole digest for the richest window is under 30k characters.
- **The signals are numbers, not prose.** A pattern row is a consumer with call count, error share and token share against a baseline; a per-day median lift; a newly off-script name or path with a count. Rendered as one sentence each, a row reads like a finding — which is what makes a blind comparison possible.
- **Two arms are needed, not one.** #21 resolved repeated correction as *model-only* and exported the placement question here: the only cheap home for it is the window's typed turns inside Stage B's digest. A finding drawn from turns traces to no pattern, so admitting turns amends ADR-0021's traceability rule. Testing that in the same run as "does B add anything over A" would confound the two questions.

## Decision

### 1. The question, and what B is measured against

*Does a model synthesis over the digest surface anything the operator would act on that the ranked pattern list does not already state?* The comparator — **A's list** — is the window's patterns as the view will render them: every row that clears its magnitude floor, one sentence per row from a fixed per-signal template, no verdict. Nothing else is held back from A to make B look better.

### 2. The criterion — two numbers, fixed now

- **Additive.** On **at least 3 of the 5** pattern windows, at least one surviving B finding is rated *act* under the blind protocol below **and** is not a restatement of a single A card. Restatement is mechanical first: a finding that cites exactly one pattern row and states only that row's numbers restates it. A finding citing two or more rows (a relation A does not state), or two or more turn locators, or one the operator marks after unblinding as saying something its cited row does not, is additive. Overrides are recorded.
- **Faithful.** Both control windows return exactly *nothing to report* — one finding on a control is no-go, whatever the additive count. Across the five pattern windows, **at most one** finding carries a claim absent from its digest (a number, a name, a session id, a turn). Two is no-go, whatever the additive count.

Go needs both. Neither number moves after the run. *Act* means the operator names, before the key is revealed, a concrete action they would take this week — open a session, change a declaration, drop or reconfigure a tool, change a habit — not "interesting".

### 3. The model

The pin, `claude-haiku-4-5-20251001`, via `claude -p` as `eval/run.py` does. **No escalation.** The map's scope guard holds the pin; the question is whether Stage B earns its place *on this machine's model*, so a failure on Haiku is a no-go, not a reason to try the next tier. One prompt (v1) is written before any digest is read; one revision (v2) is permitted for **shape** failures only — non-JSON, cap exceeded, findings dropped for traceability — never for content after a rating exists. The operator rates once, on the final arm outputs; both versions are reported.

### 4. The digest — three blocks, JSON, per project-window

- **`patterns`** — Stage A's output with ids. Pattern id `{signal}@{project}:{lo}..{hi}`; row id `{pattern-id}#{key}` where the key is the consumer name, the baseline kind, or the new name or path. Rows carry exactly the numbers the view will show (the #19 schema minus tool-use and message ids, ADR-0023) and their session ids. The window state (*too thin* / *nothing to report* / patterns) and each baseline's state (*preceding* / *history* / *no baseline*) are stated, so an empty window is a digest, not an absence.
- **`sessions`** — one line per session with usage in the window: id, date, audit title (`SKIP` or *unaudited* where that is what the table holds). Titles are already model-gated prose, the same input class as the status narrative (ADR-0012); the Did/Decided bodies are not sent.
- **`turns`** — *second arm only*: the window's distinct typed user turns, verbatim, each with its `(session id, piece index)` locator, ordered by session then index; #21's universe (2–1,500 characters, injections, interruptions and command grains excluded; one copy per (session, text)).

Never in the digest: raw JSONL, tool output, assistant text. Typed user turns already reach the same model in the what-pass, so the turn block moves no scope guard.

### 5. Two arms, and what admits the turn class

Every window runs twice: **arm A** over `patterns` + `sessions`; **arm A+T** over all three blocks. The criterion in §2 is applied to each arm. Stage B goes if **either** arm clears. The turn block is admitted as a **second evidence class** only if arm A+T clears the additive criterion on **at least 3 windows by findings that cite turns**; otherwise it is struck, and repeated correction leaves the product — Stage A cannot hold it (#21) and nothing else can.

If admitted, ADR-0021's traceability rule is amended to: *a finding traces to at least one pattern id, or to at least two turn locators from at least two distinct sessions.* One turn is a one-off, the rubric's *suggested* tier (#23), and is not a finding. Traceability is enforced in code before rating — set membership on row ids and locators — and the drop count is reported.

### 6. The dry-run finding shape

Four fields: `patterns` (row ids), `turns` (locators), `statement` (one sentence, the so-what), `change` (one concrete change — "be more careful" is not one). **At most three findings per window**, the cap fixed now. The rubric's tiers and kinds (#23) are schema for the frozen set if Stage B goes, not for the dry run.

### 7. The blind protocol

1. The dry-run script renders every A row and every surviving B finding as a card in the same shape — statement, then the change (A's change line is empty) — with no source label, shuffled per window with a fixed seed.
2. The operator rates each card *act* or *no*, writing the action for every *act*, before the key is revealed.
3. Unblind. Per B card rated *act*: the restatement test (§2), operator override recorded. Per B card: the faithfulness check — numbers as substrings of the digest, ids and locators as set membership, the residue read by the operator.
4. Rating sheets live under `local-data/eval/so-what/`, never committed; #27's resolution carries counts, window ids and session ids only.

The known limit: model prose and template prose may be tellable apart. The shared card shape and a prompt that asks for it are the mitigation; the residual bias is reported, not solved. The rater is the operator, and the operator is the product's only user — a second rater would measure someone else's product.

### 8. The five windows and two controls

Fixed now so the run cannot pick them: **hindsight-old@2026-09-07** (rich: three patterns, both baselines), **hindsight-new@2026-09-11** (no baseline of any kind), **career-ops@2026-09-11** (drift *absent* — no declaration), **content@2026-09-11** (drift from one session), **career-ops@2026-08-28** (older, thin). Controls: **thisisme@2026-09-11** (*too thin*, empty) and **thisisme@2026-07-31** (*nothing to report*). Fourteen local days each, ADR-0014 buckets; digests built from the #19 prototype's output on its branch, since the greybox's Stage A does not exist yet. The seven reserve windows are named in #27.

### 9. What each verdict leaves behind

- **No-go.** Stage A ships alone. ADR-0021's conditional clause resolves *not built*; this ADR is accepted with that verdict written in. The map's fog items for Stage B (finding schema, digest format, frozen set and threshold) are struck; ADR-0024's `status_narrative` mirror has no table to build; CONTEXT.md's *finding* is marked not built. Repeated correction leaves the product with it; the 164 labelled turns stay under `local-data/`.
- **Go.** The fog items graduate into tickets: the frozen eval set (seeded from these seven digests plus the seven reserve windows, with the two controls as its empty cases per ADR-0022), the finding schema (tiers and kinds from #23), and the pass itself mirroring `refresh_narratives` (ADR-0024). Stage B's fixed production window is decided in the schema ticket; the dry run's 14 days is the default preset, not that decision.

## Considered options

- **One arm, turns included.** Cheaper, but a go could not say whether the turns or the patterns earned it, and the traceability amendment would ride in unexamined.
- **Rate unblinded.** Half the operator time, but "would I act on this" asked of a card labelled *model* measures trust in models, not the card.
- **A judge model instead of the operator.** The pattern the narrative eval rejected: a second call, its own variance, and exactly the unverifiable thing the eval exists to catch. The set is small enough to read.
- **Escalate past Haiku on failure.** Answers a different question than the one ADR-0021 asked, and moves a scope guard the map holds.
- **≥2 of 5, or ≥4 of 5.** Two is a coin toss on five windows; four demands the synthesis add something on a window with one pattern and no baseline, which is asking B to invent.
- **Zero fabrications across the pattern windows.** The right production gate, and the frozen set will hold it; for a first prompt on a go/no-go it decides the prompt draft, not the approach. One is tolerated and reported; two is the approach.
- **Send Did/Decided bodies.** Thirty-plus kilobytes of model prose per rich window for context the titles already give; the finding is about the numbers.

## Consequences

- #27 is a throwaway script on a throwaway branch: builds the fourteen digests (seven windows × two arms), calls the pin, enforces traceability, renders the cards, records the ratings, prints the two numbers against §2. It runs only after the operator confirms this ADR on #26.
- CONTEXT.md gains *digest*; *finding* names the traceability rule and its conditional amendment.
- The map's Decisions-so-far carries the criterion in one line; the Stage B fog items are marked as waiting on #27.
- The credit for the borrowed rubric criteria (#23) lands in `docs/` with the pass if Stage B goes, not before.
