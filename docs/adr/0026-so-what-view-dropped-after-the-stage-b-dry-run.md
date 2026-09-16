# ADR-0026: The so-what view is dropped after the Stage B dry run

**Date:** 2026-09-16 · **Status:** accepted · **Decides:** the closure of map [#18](https://github.com/dempseydata/hindsight/issues/18) (operator decision, 2026-09-16), with [#28](https://github.com/dempseydata/hindsight/issues/28) and [#29](https://github.com/dempseydata/hindsight/issues/29) cancelled · **Touches:** ADR-0021, ADR-0022, ADR-0023, ADR-0024, ADR-0025, ADR-0006

## Context

Map #18 charted a fourth view: cross-session patterns stated against a project's own baseline (Stage A, mechanical), with a model synthesis over them (Stage B) conditional on a design-time eval (ADR-0021). Eight tickets resolved the signals, the window and floors, the evidence pointers, compute placement and the go/no-go criterion; the ninth ran the criterion ([#27](https://github.com/dempseydata/hindsight/issues/27), ADR-0025).

The dry run was a no-go on both arms. But the sheet said something the criterion had not asked: of the **18 Stage A rows** rendered as sentences over five real 14-day windows and rated blind by the product's only user, **one** was rated *act* — an error-share row — and the action named for it was not on the card at all: a view over tool errors by consumer, a different surface. Cost-share rows, cost-trend rows and drift rows all read as facts the operator would not act on that week. The comparator Stage B had failed to beat had itself barely cleared the product's own bar, *acted-upon insights, not interest* (`background/why.md`).

Two tickets remained: the greybox (#28), which would have calibrated the floors over real data and settled the view's layout, and the sunk-cost grilling (#29). Neither had started.

## Decision

**The so-what view is dropped, Stage A included.** The map closes with its destination not reached; #28 and #29 are closed as cancelled, not resolved. ADR-0021 to ADR-0025 stand as the record of how a view that was not built was decided, and are not amended further; CONTEXT.md marks the section as dropped and keeps its terms so the record reads.

The view returns, if ever, as a fresh effort with its own map and its own criterion — never by reopening this one. The error-analysis view the rating produced is a separate idea, unowned by this decision.

## Considered options

- **Ship Stage A alone** — ADR-0025's no-go branch as written. Rejected: the branch was written assuming the pattern list was worth having; the sheet is the first measurement of that, and it read 1 in 18.
- **Run the greybox first** (#28) to calibrate the floors before deciding. The case for it: the dry run was one operator on one day at one window length, and the floors were provisional. The case against, which won: the dry run already put the rendered rows in front of the only user, over real data, against a bar fixed in advance; a greybox re-asks the same question with layout added, and a second pass at floors after a 1-in-18 is deciding the threshold to fit the result.
- **Park it** — keep the spec complete and waiting. Rejected: a parked spec decays with the data and the tooling under it, and the map's Decisions-so-far already preserve everything a fresh effort would want to read.

## Consequences

- No fourth nav item; nothing in `build/` changes — no so-what route, no Stage A in Python, none of ADR-0024's three indexes.
- The vocabulary in CONTEXT.md's so-what section is historical; the `sessionStorage` note in *Filter state* about the so-what view navigating with query-string state describes a view that does not exist.
- `local-data/eval/so-what/` and #21's 164 labelled turns stay under `local-data/`, unused; the three prototype branches and the dry-run branch stay on the remote as the record of the code that produced the answers.
- The idea that did survive — errors by consumer as a surface of its own — is written down here and nowhere else, so that it is not mistaken for a leftover of this map.
