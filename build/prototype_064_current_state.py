"""PROTOTYPE — ticket #64 (map #59), throwaway. Never merged.

Question: can the how-view status card read as a current-state summary
(later decisions overwrite earlier), and what input does supersession need?
Renders three cards per project side by side:
  A  the stored status-v1 card (aggregate: Built / Reversed / Now)
  B  current-state prompt over the run ledger alone (titles only)
  C  the same prompt with the project's ADR headers added as a second input
Output holds real data -> local-data/prototype-064/ (gitignored). Run:
  python3 build/prototype_064_current_state.py hindsight explainer
"""
import html
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))
import how  # noqa: E402
from analyze import DEFAULT_DB, DEFAULT_PROJECTS_DIR, MODEL  # noqa: E402
from score import parse  # noqa: E402

OUT = Path(__file__).parent.parent / "local-data" / "prototype-064"

PROMPT = """You are writing the status card for one project's process view. The card is a CURRENT-STATE summary: what stands now, not everything that ever happened. Later work overwrites earlier work; what was overwritten moves to Superseded so it stays visible.

Input is JSON below: "runs" — the project's phase runs in date order (stage, start, end, audit titles of its sessions; the last run is the current one){decisions_intro}.

Output STRICT JSON, nothing else, exactly this shape:
{{"Standing": ["..."], "Superseded": ["..."], "Now": ["..."]}}

- Standing: what the project is and has, as of the last run — 3 to 8 lines. Group related work into one line and name its pieces. Leave OUT anything a later title{decisions_or} shows was dropped, replaced, retired or reversed: it belongs under Superseded instead, never in both.
- Superseded: each thing later overwritten, 0 to 5 lines, in the form "<what it was> (<date>) → <what replaced or dropped it> (<date>)". Only when the input states the later change; never infer it.
- Now: first line "<Stage>, since <Mon D>: <what the current run's titles are about>". A second line only for an open thread still in progress.

Every line carries its date(s) as month-abbreviation and day, e.g. "Sep 16" or "Aug 16–20", taken from the input's ISO dates (never a weekday), uses the input's own words, and states nothing the input does not contain. Terse facts, no markdown fences.
"""


def adr_headers(root):
    """Title + status line + touches/amends of each ADR, dated by its header
    or else by the commit that added it. Mechanical; the model judges."""
    out = []
    for f in sorted((root / "docs" / "adr").glob("*.md")):
        text = f.read_text()
        title = next((l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("# ")), f.stem)
        head = "\n".join(text.splitlines()[:8])
        date = re.search(r"\*\*Date:\*\*\s*(\d{4}-\d\d-\d\d)", head)
        date = date.group(1) if date else subprocess.run(
            ["git", "-C", str(root), "log", "--diff-filter=A", "--format=%as", "--", str(f)],
            capture_output=True, text=True).stdout.strip().split("\n")[-1]
        status = re.search(r"[Ss]tatus:\**\s*([^·\n]+)", head)
        touches = re.search(r"\*\*(?:Touches|Amends|Supersedes):\*\*\s*([^·\n]+)", head)
        out.append({"adr": f.stem[:4], "date": date, "title": title,
                    "status": status.group(1).strip()[:200] if status else None,
                    **({"touches": touches.group(1).strip()} if touches else {})})
    return out


def run_model(prompt):
    r = subprocess.run(["claude", "-p", "--model", MODEL], input=prompt,
                       capture_output=True, text=True, timeout=300)
    try:
        return parse(r.stdout)
    except ValueError:
        return {"error": [r.stdout[:500] or r.stderr[:500]]}


def card(name, groups):
    body = "".join(f"<h4>{html.escape(g)}</h4><ul>" + "".join(
        f"<li>{html.escape(str(x))}</li>" for x in (lines or ["—"])) + "</ul>"
        for g, lines in groups.items())
    return f"<section><h3>{html.escape(name)}</h3>{body}</section>"


def main(projects):
    conn = sqlite3.connect(f"file:{DEFAULT_DB}?mode=ro", uri=True)
    OUT.mkdir(parents=True, exist_ok=True)
    page = []
    for p in projects:
        root = Path(DEFAULT_PROJECTS_DIR) / p
        d = how.how_data(conn, p)
        ledger = {"runs": d["runs"]}
        stored = how.narrative(conn, p, d)
        adrs = adr_headers(root)
        b = run_model(PROMPT.format(decisions_intro="", decisions_or="")
                      + "\n" + json.dumps(ledger, indent=1))
        c = (run_model(PROMPT.format(
            decisions_intro='; "decisions" — the project\'s ADRs (number, date, title, status line, what each touches). A decision whose status says superseded/amended, or a later ADR whose title drops or replaces something, is a later change',
            decisions_or=" or decision")
            + "\n" + json.dumps({**ledger, "decisions": adrs}, indent=1))
            if adrs else {"note": ["no ADRs in this project — C is identical to B"]})
        json.dump({"stored": stored, "B": b, "C": c, "adrs": adrs},
                  open(OUT / f"{p}.json", "w"), indent=1)
        runs = "".join(f"<li><b>{r['stage']}</b> {r['start']}–{r['end']}: "
                       f"{html.escape('; '.join(r['titles']))}</li>" for r in reversed(d["runs"]))
        page.append(f"<h2>{p}</h2><div class=row>"
                    + card("A · stored status-v1 (aggregate)", stored["facts"] if stored else {"none": []})
                    + card("B · current-state, titles only", b)
                    + card(f"C · current-state + {len(adrs)} ADR headers", c)
                    + f"</div><details><summary>Run ledger — the reachable history ({len(d['runs'])} runs, never rewritten)</summary><ul>{runs}</ul></details>")
    (OUT / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>PROTOTYPE 064</title><style>"
        "body{font:14px/1.5 system-ui;margin:24px;max-width:1500px}"
        ".row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}"
        "section{border:1px solid #ccc;border-radius:6px;padding:8px 14px}"
        "h4{margin:8px 0 2px}</style><p><b>PROTOTYPE — ticket #64, throwaway, real data, never commit.</b></p>"
        + "".join(page))
    print(OUT / "index.html")


if __name__ == "__main__":
    main(sys.argv[1:] or ["hindsight", "explainer"])
