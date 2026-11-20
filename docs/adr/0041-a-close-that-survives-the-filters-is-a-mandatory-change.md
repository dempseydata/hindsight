# ADR-0041: A close that survives the finished-work filters is a mandatory change

**Date:** 2026-11-20 · **Status:** accepted · **Amends:** ADR-0040 (§1, §3) · **Decides:** issue #96 (map #59, v2 audit core)

## Context

ADR-0040 made strong changes mandatory and left a "close" change to the model, to judge whether a thing was abandoned. Under the 39/45 bar (eval/README.md, operator decision 2026-11-20), that judgement is now the only failure that repeats.

- **The failure.** `v2-p13` pooled 37/45 over three sweeps. `thisisme@live`'s "close OpenSpec" was missed in 3 of 9 calls, which is 3 of the 8 failed calls. Every other Superseded fact passed at least 8 of 9. Without that miss the pool is 40/45.
- **Strong changes are followed; close changes are not.** Across `v2-p11`, `v2-p12` and `v2-p13` (75 calls), a strong change went unlisted once (M7). The one close change that is an abandonment was missed 3 times in the 9 `v2-p13` calls, and the model is the only thing judging it.
- **Close parts are few, and the finished ones are recognisable.** After ADR-0040's ticket filter, the five frozen cases hold 5 unique close parts, and only "close OpenSpec" is an abandonment. The other four close research ("rubric research closes"), a decision ("closed palette decision"), a grilled question ("Grilled and closed: readability look…") or a body of work ("restyle close-out"). A read-only pass over the local store (404 audited sessions, 23 projects, kept out of git) found one more: "close it", from a hindsight title that closes issue #95. The comma split cut it off from its "#95", so it names no thing of its own.
- **The judgement is already written down as a rule.** The prompt says that closing research, a decision or a piece of work is finished work. That rule is mechanical enough to live in code, as the strong verbs moved there under ADR-0040.

## Decision

1. **`title_changes` drops two more forms of finished close** before a close becomes a change:
   - **an inquiry closed**: the part names research, a decision, a question or a grilling (`research`, `decision(s)`, `question(s)`, `grill(ed|ing)`), or is a `close-out`;
   - **nothing named**: the part has no content word (`score.words`) other than the verb itself, as in "close it".

   ADR-0040's ticket, map, issue, phase and `#N` filter stays.
2. **A close that survives the filters is a strong change.** It is listed under `changes`, binds M7, and must get a Superseded line. The `kind` field goes, because every listed change is now mandatory. The prompt's rule 2 drops "a close change gets a line only when a thing was abandoned" and keeps the "close the team wiki" example.
3. **No case, anchor or floor moves.** M7 already binds every listed change. The cases' `changes` are re-derived at call time, as ADR-0040 §2 set out.

This amends ADR-0040 §1 (the close kind and its filter) and §3 (the model no longer judges a close). The model still judges every supersession drawn from ADRs.

## Alternatives rejected

- **A p14 prompt rule.** The prompt already states the rule and gives a near-identical example. Prompt rules aimed at thisisme have made it worse before (`v2-p10`).
- **Make every close mandatory.** Four of the five frozen close parts are finished work. Each would become a wrong Superseded line, which M2 and the anchors would then fail.
- **Apply the ticket filter to the whole title instead of the part.** It catches "close it", but a title that closes a ticket and abandons a thing ("Close ticket 8; close the team wiki") would lose the abandonment. The no-thing-named filter catches the same case without that loss.
- **Retire the OpenSpec anchor.** It is a frozen ground-truth fact, and the card is wrong without it. Moving the anchor to pass the eval is moving the goalposts.

## Consequences

- **The rule is fitted to the evidence it was drawn from.** It has one positive example ("close OpenSpec") and five negatives, across 404 sessions. A finished close in a new form, such as "closed the spike" or "closed the review", becomes a mandatory Superseded line. As with ADR-0040's strong verbs, the fix belongs in the filter list, not the prompt.
- **`grill` is the operator's own word** for a decision session (the `grilling` skill). It is in the list because this tool has one operator. Another user's vocabulary would need its own words.
- **Making the close mandatory moves the failure; it does not hide it.** In the eval, a missed OpenSpec line now fails M7 as well as the anchor, and the case fails either way. The expected gain is that the model obeys the mandatory list, as it does for strong changes (1 unlisted in 75 calls). Live, the write-time gate refuses such a card and the next run retries.
- **Before the next sweep:**
  - the selfcheck gains a close-out case and a no-thing-named case;
  - the `TitleChanges` tests lose `kind` and gain the two filters;
  - ACCEPT is three fresh sweeps of the amended prompt, pooled against 39/45.
- **CONTEXT.md:** **Title change** loses the strong/close distinction.
- ADR-0040's status line reads "accepted; §1 and §3 amended by ADR-0041".
