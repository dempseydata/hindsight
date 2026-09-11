"""PROTOTYPE — throwaway (ticket #21). Does a mechanical definition of a corrective turn hold?

python3 prototype/correction.py sample   # build the labelling sheet (local-data, never committed)
python3 prototype/correction.py score    # score heuristics against the hand labels
"""
import re, sys, glob, json, random, sqlite3, collections, csv

EX = "local-data/analysis/extracts/"
SHEET = "local-data/analysis/prototype/correction-labels.tsv"
SEED = 21
PIECE = re.compile(r"^\[(\d+)\] (USER|ASSISTANT|TOOL): (.*?)(?=^\[\d+\] (?:USER|ASSISTANT|TOOL): |\Z)", re.S | re.M)

# v1 — written before labelling. v2 — one permitted revision after labelling (see score()).
OPEN_V1 = re.compile(r"^(no\b|nope|not (that|what|quite|there|like)|that'?s (not|wrong)|wrong|incorrect|don'?t|do not|stop|undo|revert|roll ?back|again\b|still\b|why (did|have|are) you|you('ve| have)? (missed|forgot|ignored|didn'?t|did not|changed|broke|removed|deleted|skipped)|i (said|asked|told|meant|didn'?t (ask|say|want))|as i said|instead|actually|hang on|wait|hold on|that (broke|isn'?t|is not)|re-?read|you'?re wrong|this is wrong|hmm|erm|um\b)", re.I)
IN_V1 = re.compile(r"\b(i said|i asked for|not what i|you didn'?t|you ignored|you missed|as i said|i meant|that'?s not what|you were (supposed|asked|told)|i told you|should have|shouldn'?t have|go back to)\b", re.I)
# v2 — the one permitted revision, written after labelling v1's sample: bare "no" and "actually" dropped
# (5 of v1's 10 distinct false positives), wording-rewrite and still-broken phrasings added (v1's two observed misses).
OPEN_V2 = re.compile(r"^(no\b\s*[,\-\u2013!:]|no[,.]?\s+(that|it|this|you|we|not)\b|nope|not (that|what|quite|there|like)|that'?s (not|wrong)|wrong|incorrect|don'?t|do not|stop|undo|revert|roll ?back|again\b|still\b|why (did|have|are) you|you('ve| have)? (missed|forgot|ignored|didn'?t|did not|changed|broke|removed|deleted|skipped)|i (said|told|meant|didn'?t (ask|say|want))|as i said|instead|hang on|wait|hold on|that (broke|isn'?t|is not)|re-?read|you'?re wrong|this is wrong|there should|we missed)", re.I)
IN_V2 = re.compile(r"\b(i said|not what i|you didn'?t|you ignored|you missed|as i said|i meant|that'?s not what|you were (supposed|asked|told)|i told you|should have|shouldn'?t have|does not read right|doesn'?t read (right|well)|re-?phrase|reword|change the way you|the way you (phrase|word)|should (have been|be) (classed|dated|named|called|filed)|missed a step|missed the|still not|isn'?t working|doesn'?t work|does not work|not working|unable to|the bug is|not carried)\b", re.I)
SHEET2 = "local-data/analysis/prototype/correction-labels-v2.tsv"

def hit(t, v=1):
    o, i = (OPEN_V1, IN_V1) if v == 1 else (OPEN_V2, IN_V2)
    return bool(o.search(t[:80]) or i.search(t))

def load():
    db = sqlite3.connect("local-data/hindsight.db")
    proj = dict(db.execute("select id, project from sessions"))
    seqs = collections.defaultdict(list)  # sid -> [(idx, role, text)]
    for p in sorted(glob.glob(EX + "*.part*.txt")):
        sid = p.split("/")[-1].split(".")[0]
        txt = open(p, encoding="utf-8", errors="replace").read()
        for m in PIECE.finditer(txt):
            seqs[sid].append((int(m.group(1)), m.group(2), m.group(3).strip()))
    for s in seqs: seqs[s].sort()
    return proj, seqs

def typed(t):
    return 2 <= len(t) <= 1500 and not t.startswith(("<", "[Request interrupted"))

def universe(proj, seqs):
    return [(sid, idx, proj.get(sid, "?"), t) for sid, ps in seqs.items() for idx, role, t in ps if role == "USER" and typed(t)]

def sample():
    proj, seqs = load()
    U = universe(proj, seqs)
    hits = [u for u in U if hit(u[3])]; non = [u for u in U if not hit(u[3])]
    rnd = random.Random(SEED)
    H = hits if len(hits) <= 40 else rnd.sample(hits, 40)
    N = rnd.sample(non, 60)
    rows = [(*u, 1) for u in H] + [(*u, 0) for u in N]
    rnd.shuffle(rows)
    with open(SHEET, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["sid", "idx", "project", "v1_hit", "label", "text"])
        for sid, idx, pr, t, h in rows:
            w.writerow([sid, idx, pr, h, "", t.replace("\t", " ").replace("\n", " ⏎ ")[:400]])
    print(f"universe {len(U)} typed turns, sessions {len({u[0] for u in U})}; v1 hits {len(hits)} in {len({u[0] for u in hits})} sessions; sheet: {len(H)} hits + {len(N)} non-hits -> {SHEET}")

def sample2():
    """Fresh rows for v2: its unlabelled hits (cap 40) + 60 random v2 non-hits not already labelled."""
    proj, seqs = load(); U = universe(proj, seqs)
    done = {(r["sid"], int(r["idx"])) for r in csv.DictReader(open(SHEET), delimiter="\t")}
    rnd = random.Random(SEED + 1)
    hits = [u for u in U if hit(u[3], 2) and (u[0], u[1]) not in done]
    non = [u for u in U if not hit(u[3], 2) and (u[0], u[1]) not in done]
    H = hits if len(hits) <= 40 else rnd.sample(hits, 40); N = rnd.sample(non, 60)
    rows = [(*u, 1) for u in H] + [(*u, 0) for u in N]; rnd.shuffle(rows)
    with open(SHEET2, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t"); w.writerow(["sid", "idx", "project", "v2_hit", "label", "text"])
        for sid, idx, pr, t, h in rows: w.writerow([sid, idx, pr, h, "", t.replace("\t", " ").replace("\n", " \u23ce ")[:400]])
    print(f"v2 hits {sum(1 for u in U if hit(u[3], 2))} in {len({u[0] for u in U if hit(u[3], 2)})} sessions; new to label: {len(H)} hits + {len(N)} non-hits -> {SHEET2}")

def score():
    proj, seqs = load()
    U = universe(proj, seqs)
    text = {(u[0], u[1]): u[3] for u in U}
    sheets = {1: SHEET, 2: SHEET2}
    lab = {}
    for v, sh in sheets.items():
        try: rows = list(csv.DictReader(open(sh), delimiter="\t"))
        except FileNotFoundError: continue
        assert all(r["label"] in ("0", "1") for r in rows), f"label every row 0/1 in {sh}"
        for r in rows: lab[(r["sid"], int(r["idx"]))] = int(r["label"])
    fresh = {(r["sid"], int(r["idx"])) for r in csv.DictReader(open(SHEET2), delimiter="\t")} if 2 in sheets and OPEN_V2 else set()
    # distinct (sid, text): a turn re-sent verbatim in one session counts once — 915 extra copies in 22 sessions otherwise
    key = lambda k: (k[0], text[k])
    for v in (1, 2):
        if v == 2 and OPEN_V2 is None: break
        hits = {(u[0], u[1]) for u in U if hit(u[3], v)}
        lh = {key(k): lab[k] for k in lab if k in hits}
        pool = fresh if v == 2 else set(lab)           # v2 recall only from the fresh non-hit sample
        ln = {key(k): lab[k] for k in pool if k not in hits}
        n_hit_d = len({key(k) for k in hits}); n_non_d = len({key((u[0], u[1])) for u in U}) - n_hit_d
        tp = sum(lh.values()); fp = len(lh) - tp; miss = sum(ln.values())
        est_miss = miss / len(ln) * n_non_d if ln else 0
        prec = tp / len(lh) if lh else 0; rec = tp / (tp + est_miss) if tp + est_miss else 0
        print(f"v{v} (distinct turns): hits {n_hit_d} | labelled hits {len(lh)} tp {tp} fp {fp} -> precision {prec:.2f} | labelled non-hits {len(ln)}, corrections {miss} -> est. missed {est_miss:.0f}, recall {rec:.2f}")
    # prevalence and the kill test (can anything repeat?)
    tps = [k for k, l in lab.items() if l]
    prev_hit = sum(lab[k] for k in lab if hit(text[k])) / max(1, sum(1 for k in lab if hit(text[k])))
    n_hits = sum(1 for u in U if hit(u[3])); n_non = len(U) - n_hits
    miss_rate = sum(lab[k] for k in lab if not hit(text[k])) / max(1, sum(1 for k in lab if not hit(text[k])))
    est_total = prev_hit * n_hits + miss_rate * n_non
    print(f"estimated true corrections in universe {est_total:.0f} of {len(U)} = {est_total/len(U):.1%}")
    per = collections.Counter((proj.get(k[0], '?'), k[0]) for k in tps)
    by_proj = collections.defaultdict(int)
    for (pr, sid), c in per.items():
        if c >= 2: by_proj[pr] += 1
    print("labelled sessions with >=2 true corrections, per project:", dict(by_proj) or "none")
    # second-order: repeat by phrasing, repeat by next tool
    def toks(t): return set(re.findall(r"[a-z]{3,}", t.lower()))
    pairs = 0
    for a in tps:
        for b in tps:
            if a < b and a[0] != b[0] and proj.get(a[0]) == proj.get(b[0]):
                ta, tb = toks(text[a]), toks(text[b])
                if ta and tb and len(ta & tb) / len(ta | tb) >= 0.5: pairs += 1
    print("near-duplicate correction pairs across sessions of one project (jaccard>=0.5):", pairs)
    same_tool = 0; with_tool = 0
    for sid, idx in tps:
        ps = seqs[sid]; i = next(j for j, p in enumerate(ps) if p[0] == idx)
        before = next((p[2].split(":")[0].strip("[") for p in reversed(ps[:i]) if p[1] == "TOOL"), None)
        after = next((p[2].split(":")[0].strip("[") for p in ps[i+1:] if p[1] == "TOOL"), None)
        if before and after: with_tool += 1; same_tool += before == after
    print(f"true corrections with a tool before and after: {with_tool}; same tool name both sides: {same_tool}")
    base_same = base_with = 0
    for sid, idx in [k for k, l in lab.items() if not l]:
        ps = seqs[sid]; i = next(j for j, p in enumerate(ps) if p[0] == idx)
        before = next((p[2].split(":")[0].strip("[") for p in reversed(ps[:i]) if p[1] == "TOOL"), None)
        after = next((p[2].split(":")[0].strip("[") for p in ps[i+1:] if p[1] == "TOOL"), None)
        if before and after: base_with += 1; base_same += before == after
    print(f"base rate, labelled non-corrections: {base_with} with tools both sides; same tool: {base_same}")

if __name__ == "__main__":
    {"sample": sample, "sample2": sample2, "score": score}[sys.argv[1]]()
