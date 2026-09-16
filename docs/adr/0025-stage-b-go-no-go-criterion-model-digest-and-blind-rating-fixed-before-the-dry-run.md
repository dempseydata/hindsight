# ADR-0025: Stage B's go/no-go — criterion, model, digest and blind rating fixed before the dry run

**Date:** 2026-09-12 · **Status:** accepted — confirmed by the operator on #26 (2026-09-15); the dry run ([#27](https://github.com/dempseydata/hindsight/issues/27), 2026-09-16) returned **no-go on both arms** (arm A: additive 1/5, 2 unsupported claims; arm A+T: additive 0/5, no turn-citing finding on a corrective label; controls empty), so §9's no-go branch applies: Stage A ships alone, the turn class is not admitted, and the numbers here are the record of what was fixed before the run · **Decides:** [issue #26](https://github.com/dempseydata/hindsight/issues/26); map [#18](https://github.com/dempseydata/hindsight/issues/18) · **Touches:** ADR-0021, ADR-0022, ADR-0023, ADR-0024, ADR-0012

## Context

ADR-0021 made Stage B conditional: a design-time eval over real project-windows decides whether a model synthesis adds anything over the ranked pattern list, *against a criterion fixed before the run*. This ADR is that fixing. It is committed before the dry run ([#27](https://github.com/dempseydata/hindsight/issues/27)) so that git, not memory, proves the order; nothing here moves after #27's numbers exist.

Facts the decision rests on, read from `local-data/` on 2026-09-12 (never committed):

- **Windows exist.** At 14 days, twelve project-windows clear ADR-0022's sparsity floor and carry at least one pattern under the prototype's floors: hindsight-old ×4, career-ops ×4, content ×2, hindsight-new ×1, thisisme ×1 (thisisme@2026-08-28, one cost-trend pattern). Three control windows are available — thisisme@2026-09-11 is empty (*too thin*), thisisme@2026-07-31 has activity and nothing above the floor (*nothing to report*), content@2026-08-28 has two sessions over two days (*too thin*). The dry run uses five pattern windows and two controls (§8); seven pattern windows and the third control stay in reserve for a frozen eval set if Stage B goes.
- **A window's typed turns fit one call.** Distinct typed user turns per (session, text) — the universe #21 defined — run 80–190 per active window, 6–18k characters. Every session in the named windows has an audit; titles average 64 characters, so the largest window's titles are about 3k characters. The whole digest for the richest window is under 30k characters.
- **The signals are numbers, not prose.** A pattern row is a consumer with call count, error share and token share against a baseline; a per-day median lift; a newly off-script name or path with a count. Rendered as one sentence each, a row reads like a finding — which is what makes a blind comparison possible.
- **Typed turns are already model-read.** The what-pass sends every session's extract, typed user turns included, to the same pinned model; a *typed turn* is a `USER:` piece of 2–1,500 characters that is not an injection, an interruption or a command grain, counted once per (session, text) — #21's universe.
- **Two arms are needed, not one.** #21 resolved repeated correction as *model-only* and exported the placement question here: the only cheap home for it is the window's typed turns inside Stage B's digest. A finding drawn from turns traces to no pattern, so admitting turns amends ADR-0021's traceability rule. Testing that in the same run as "does B add anything over A" would confound the two questions.

## Decision

### 1. The question, and what B is measured against

*Does a model synthesis over the digest surface anything the operator would act on that the ranked pattern list does not already state?* The comparator — **A's list** — is the window's patterns as the view will render them: every row that clears its magnitude floor, one sentence per row from a fixed per-signal template, no verdict. A rendered row, or a rendered finding, is a **card** — the unit the operator rates (§7). Nothing else is held back from A to make B look better.

Floors for the dry run: ADR-0022's shape with the #19 prototype's values — calls ≥ 10, error share ≥ 0.10 or token share ≥ 0.25, |median lift| ≥ 0.30, new name or path ≥ 3 — and ADR-0022's sparsity floor (3 sessions, 3 active days) for window and baselines in place of the prototype's five base days. The greybox may move these values later; the values used are recorded on #27 so the comparator is known.

### 2. The criterion — two numbers, fixed now

- **Additive.** On **at least 3 of the 5** pattern windows, at least one surviving B finding is rated *act* under the blind protocol below **and** is not a restatement of a single A card. Restatement is mechanical first: a finding that cites exactly one pattern row and states only that row's numbers restates it. A finding citing two or more rows, or two or more turn locators, is additive by default; the operator's override after unblinding runs **both ways** — a single-row finding may be marked additive when it says something its cited row does not, and a multi-row finding may be marked a restatement when it says nothing its cited rows do not jointly say (a concatenation of two cards is not a relation). Overrides are recorded either way.
- **Faithful.** Both control windows return an **empty findings list** — the digest already states *too thin* or *nothing to report* (ADR-0022's words are Stage A's, never B's), and one finding on a control is no-go, whatever the additive count. Across the five pattern windows, **at most one** finding carries a claim absent from its digest (a number, a name, a session id, a turn). Two is no-go, whatever the additive count.

Go needs both. Neither number moves after the run. *Act* means the operator names, before the key is revealed, a concrete action they would take this week — open a session, change a declaration, drop or reconfigure a tool, change a habit — not "interesting".

### 3. The model

The pin, `claude-haiku-4-5-20251001`, via `claude -p` as `eval/run.py` does. **No escalation.** The map's scope guard holds the pin; the question is whether Stage B earns its place *on this machine's model*, so a failure on Haiku is a no-go, not a reason to try the next tier. One prompt (v1) is written before any digest is read; one revision (v2) is permitted, and it may change only the **shape** instructions — output format, the cap, the traceability fields — after a shape failure (non-JSON, cap exceeded, findings dropped for traceability). The content instructions are frozen at v1. The operator rates once, on the final arm outputs; both versions are reported.

### 4. The digest — three blocks, JSON, per project-window

- **`patterns`** — Stage A's output with ids. Pattern id `{signal}@{project}:{lo}..{hi}`; row id `{pattern-id}#{key}` where the key is the consumer name, the baseline kind, or the new name or path. Rows carry exactly the numbers the view will show (the #19 schema minus tool-use and message ids, ADR-0023) and their session ids. The window state (*too thin* / *nothing to report* / patterns) and each baseline's state (*preceding* / *history* / *no baseline*) are stated, so an empty window is a digest, not an absence.
- **`sessions`** — one line per session with usage in the window: id, date, audit title (`SKIP` or *unaudited* where that is what the table holds). Titles are already model-gated prose, the same input class as the status narrative (ADR-0012); the Did/Decided bodies are not sent.
- **`turns`** — *arm A+T only (§5)*: the window's distinct typed turns, verbatim, each with its `(session id, piece index)` locator, ordered by session then index; #21's universe (2–1,500 characters, injections, interruptions and command grains excluded; one copy per (session, text)).

Never in the digest: raw JSONL, tool output, assistant text. Typed user turns already reach the same model in the what-pass, so the turn block moves no scope guard.

### 5. Two arms, and what admits the turn class

Every window runs twice: **arm A** over `patterns` + `sessions`; **arm A+T** over all three blocks. The criterion in §2 is applied to each arm. Stage B goes if **arm A clears**, or if **arm A+T clears the additive criterion on at least 3 windows by findings that cite turns** — the same condition that admits the turn block as a **second evidence class**. Arm A+T clearing on pattern-only findings where arm A did not is the same input sampled twice, not evidence: it is reported and does not count. If the turn condition fails, the turn block is struck and repeated correction leaves the product — Stage A cannot hold it (#21) and nothing else can.

If admitted, ADR-0021's traceability rule is amended to: *a finding traces to at least one pattern id, or to at least two turn locators from at least two distinct sessions.* One turn is a one-off, the rubric's *suggested* tier (#23), and is not a finding. Traceability is enforced in code before rating — set membership on row ids and locators — and the drop count is reported.

Two consequences follow on a go with turns admitted, so they are fixed now rather than discovered. **Click-through:** the piece index is for the code-side check and the eval only; the served target of a turn-traced finding is the session anchor, `/what#<session-id>` (ADR-0023) — nothing served follows a piece, exactly as nothing follows a tool-use id. **Storage key:** ADR-0024 keys a stored Stage B row on the hash of the window's pattern set; with turns in the digest the key is the hash of the **whole digest**, patterns and turn set, or a new session's turns would move B's input and leave a stale row unhidden.

### 6. The dry-run finding shape

Four fields: `patterns` (row ids), `turns` (locators), `statement` (one sentence, the so-what), `change` (one concrete change — "be more careful" is not one). **At most three findings per window**, the cap fixed now. The rubric's tiers and kinds (#23) are schema for the frozen set if Stage B goes, not for the dry run.

### 7. The blind protocol

1. The dry-run script renders every A row and every surviving B finding as a card in the same shape — statement, then the change (A's change line is empty) — with no source label, shuffled per window with a fixed seed.
2. The operator rates each card *act* or *no*, writing the action for every *act*, before the key is revealed.
3. Unblind. Per B card rated *act*: the restatement test (§2), operator override recorded. Per B card: the faithfulness check — numbers as substrings of the digest, ids and locators as set membership, the residue read by the operator.
4. Rating sheets live under `local-data/eval/so-what/`, never committed; #27's resolution carries counts, window ids and session ids only.

Two known limits. Model prose and template prose may be tellable apart — the shared card shape and a prompt that asks for it are the mitigation; the residual bias is reported, not solved. And without the rubric's `kind` field (#23), a cost cluster restated as a behavioural lesson can read as additive — the restatement test is the mitigation, and the unblinded pass names any such case.

The too-thin control tests a case production never runs — ADR-0024 computes Stage B only where a pattern set exists — and is kept because an empty digest is the cheapest probe of whether the prompt manufactures findings from nothing. The rater is the operator, and the operator is the product's only user — a second rater would measure someone else's product.

### 8. The five windows and two controls

Fixed now so the run cannot pick them: **hindsight-old@2026-09-07** (rich: three patterns, both baselines), **hindsight-new@2026-09-11** (no baseline of any kind), **career-ops@2026-09-11** (drift *absent* — no declaration), **content@2026-09-11** (drift from one session), **career-ops@2026-08-28** (older, thin). Controls: **thisisme@2026-09-11** (*too thin*, empty) and **thisisme@2026-07-31** (*nothing to report*). Fourteen local days each, ADR-0014 buckets; digests built from the #19 prototype's output on its branch, since the greybox's Stage A does not exist yet. The seven reserve windows are named in #27.

### 9. What each verdict leaves behind

- **No-go.** Stage A ships alone. ADR-0021's conditional clause resolves *not built*; this ADR is accepted with that verdict written in. The map's fog items for Stage B (finding schema, digest format, frozen set and threshold) are struck; ADR-0024's `status_narrative` mirror has no table to build; CONTEXT.md's *finding* is marked not built. Repeated correction leaves the product with it; the 164 labelled turns from #21 stay under `local-data/`, unused.
- **Go.** The fog items graduate into tickets: the frozen eval set (seeded from the dry run's fourteen digests plus the reserve windows, the controls as its empty cases per ADR-0022, and — if the turn class is admitted — #21's 164 labelled turns as the ground truth for turn-citing findings, reviewed before anything enters `eval/`), the finding schema (tiers and kinds from #23), and the pass itself mirroring `refresh_narratives` (ADR-0024). Stage B's fixed production window is decided in the schema ticket; the dry run's 14 days is the default preset, not that decision.

## Considered options

- **One arm, turns included.** Cheaper, but a go could not say whether the turns or the patterns earned it, and the traceability amendment would ride in unexamined.
- **Rate unblinded.** Half the operator time, but "would I act on this" asked of a card labelled *model* measures trust in models, not the card.
- **A judge model instead of the operator.** The pattern the narrative eval rejected: a second call, its own variance, and exactly the unverifiable thing the eval exists to catch. The set is small enough to read.
- **Escalate past Haiku on failure.** Answers a different question than the one ADR-0021 asked, and moves a scope guard the map holds.
- **≥2 of 5, or ≥4 of 5.** Two is a coin toss on five windows; four demands the synthesis add something on a window with one pattern and no baseline, which is asking B to invent.
- **Zero fabrications across the pattern windows.** The right production gate, and the frozen set will hold it; for a first prompt on a go/no-go it decides the prompt draft, not the approach. One is tolerated and reported; two is the approach.
- **Send Did/Decided bodies.** Thirty-plus kilobytes of model prose per rich window for context the titles already give; the finding is about the numbers.

## Consequences

- #27 is a throwaway script on a throwaway branch: builds the fourteen digests (seven windows × two arms), calls the pin, enforces traceability, renders the cards, records the ratings, prints the two numbers against §2 — and, as a reported statistic only, how many turn-citing findings land on a turn #21 labelled corrective. It runs only after the operator confirms this ADR on #26, and its resolution flips this ADR's status line to *accepted* with the verdict written in.
- CONTEXT.md gains *digest* and *typed turn*; *finding* names the traceability rule and points here for the conditional amendment. The cap and the finding schema stay out of CONTEXT.md until a go.
- The map's Decisions-so-far carries the criterion in one line; the Stage B fog items are marked as waiting on #27.
- The credit for the borrowed rubric criteria (#23) lands in `docs/` with the pass if Stage B goes, not before.
