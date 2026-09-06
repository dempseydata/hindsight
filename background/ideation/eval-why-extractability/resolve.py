#!/usr/bin/env python3
"""Red-team test 3: can paraphrased model quotes be fuzzy-resolved to true source spans?

For each evidence quote in an output file, scan the extract with a word-window
SequenceMatcher and report the best-matching span and its score.

Usage: resolve.py OUTPUT.json EXTRACT.txt [threshold]
"""
import difflib
import json
import re
import sys
from pathlib import Path


def words(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()


def best_span(quote_words, corpus_words, pad=8):
    n = len(quote_words)
    best = (0.0, 0, 0)
    step = max(1, n // 4)
    for start in range(0, max(1, len(corpus_words) - n + 1), step):
        window = corpus_words[start : start + n + pad]
        score = difflib.SequenceMatcher(None, quote_words, window).ratio()
        if score > best[0]:
            best = (score, start, start + n + pad)
    # refine around the winner
    lo = max(0, best[1] - step)
    for start in range(lo, best[1] + step):
        window = corpus_words[start : start + n + pad]
        score = difflib.SequenceMatcher(None, quote_words, window).ratio()
        if score > best[0]:
            best = (score, start, start + n + pad)
    return best


def main():
    out_path, extract_path = Path(sys.argv[1]), Path(sys.argv[2])
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
    corpus_words = words(extract_path.read_text())
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", out_path.read_text().strip())
    total = resolved = 0
    for f in json.loads(raw):
        for q in f.get("evidence", []):
            total += 1
            score, a, b = best_span(words(q), corpus_words)
            ok = score >= threshold
            resolved += ok
            span = " ".join(corpus_words[a:b])
            print(f"[{score:.2f} {'OK' if ok else 'MISS'}] {q[:70]}")
            print(f"      -> {span[:110]}")
    print(f"\nresolved {resolved}/{total} = {100*resolved/total:.0f}% at threshold {threshold}")


if __name__ == "__main__":
    main()
