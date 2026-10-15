"""Structural checks shared by the product-owner tasks (PO-01, PO-02).

Usage: python po_checks.py <run-dir> <rule> [arg]
Rules: count <min> | template | criteria | visual | copy | dependencies | none-dependency | english | testable
       | topics <min> <topic-json-file> | forbidden <regex-file>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ALLOWED = ["## Acceptance Criteria", "## Dependencies", "## Visual Definition", "## Copy (FR/EN)"]
VAGUE = re.compile(r"\b(user[- ]friendly|intuitive|fast|quick(ly)?|nice|beautiful|modern|easy|seamless|robust|appropriate(ly)?|properly|should work)\b", re.I)
FRENCH_WORDS = re.compile(r"\b(le|la|les|des|une|est|avec|pour|dans|être|avis|produit|utilisateur)\b", re.I)


def stories(run: Path) -> list[Path]:
    folder = run / ".user-stories"
    return sorted(p for p in folder.glob("*.md")) if folder.exists() else []


def sections(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if l.startswith("## ")]


def section(text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def criteria(text: str) -> list[str]:
    return re.findall(r"^\s*-\s*\[[ xX]\]\s*(.+)$", section(text, "## Acceptance Criteria"), re.M)


def fail(msg: str) -> None:
    print(msg)
    sys.exit(1)


def main() -> None:
    run, rule = Path(sys.argv[1]), sys.argv[2]
    arg = sys.argv[3] if len(sys.argv) > 3 else None
    files = stories(run)
    texts = {p.name: p.read_text(encoding="utf-8") for p in files}
    if not texts and rule not in ("count", "forbidden"):
        fail("no story in .user-stories/")

    if rule == "count":
        bad = [n for n in texts if not re.fullmatch(r"\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md", n)]
        numbers = sorted(int(n[:2]) for n in texts if n[:2].isdigit())
        if len(texts) < int(arg) or not numbers: fail(f"{len(texts)} stories, expected at least {arg}")
        if bad: fail(f"bad file names: {bad}")
        if numbers != list(range(numbers[0], numbers[0] + len(numbers))): fail(f"numbering not contiguous: {numbers}")
    elif rule == "template":
        for n, t in texts.items():
            if not t.startswith("# "): fail(f"{n}: no '# Title' first line")
            secs = sections(t)
            if secs[:2] != ALLOWED[:2]: fail(f"{n}: sections must start with Acceptance Criteria, Dependencies: {secs}")
            extra = [s for s in secs if not any(s.startswith(a.split(' (')[0]) for a in ALLOWED)]
            if extra: fail(f"{n}: sections not allowed for product-owner: {extra}")
    elif rule == "criteria":
        for n, t in texts.items():
            c = criteria(t)
            if len(c) < 2: fail(f"{n}: fewer than 2 criteria")
            if re.search(r"^\s*-\s*\[[xX]\]", section(t, "## Acceptance Criteria"), re.M): fail(f"{n}: criteria already checked")
    elif rule == "visual":
        for n, t in texts.items():
            v = section(t, "## Visual Definition")
            if v and not all(re.search(rf"{k}\s*:", v, re.I) for k in ("Appearance", "Needs", "Rationale")): fail(f"{n}: Visual Definition lacks Appearance/Needs/Rationale")
        if not any(section(t, "## Visual Definition") for t in texts.values()): fail("no story defines a visible element")
    elif rule == "copy":
        for n, t in texts.items():
            if section(t, "## Visual Definition"):
                c = section(t, "## Copy (FR/EN)")
                rows = [r for r in c.splitlines() if r.startswith("|") and not re.match(r"^\|\s*-", r)]
                if not rows or not re.match(r"^\|\s*Element\s*\|\s*English\s*\|\s*French\s*\|", rows[0]): fail(f"{n}: Copy (FR/EN) table missing or wrong header")
                body = [r for r in rows[1:] if len([x for x in r.split("|")[1:-1] if x.strip()]) >= 3]
                if not body: fail(f"{n}: Copy table has no complete EN/FR row")
    elif rule == "dependencies":
        names = set(texts)
        for n, t in texts.items():
            deps = [d.strip(" -`*") for d in section(t, "## Dependencies").splitlines() if d.strip().startswith("-")]
            if not deps: fail(f"{n}: empty Dependencies")
            for d in deps:
                if d.lower().startswith("none"):
                    continue
                target = re.search(r"\d{2}-[a-z0-9-]+\.md", d)
                if not target or target.group(0) not in names: fail(f"{n}: dependency '{d}' is not an existing story file")
                if target.group(0) >= n: fail(f"{n}: depends on a later story {target.group(0)}")
    elif rule == "none-dependency":
        if not any(re.search(r"^\s*-\s*`?None", section(t, "## Dependencies"), re.M) for t in texts.values()): fail("no independent story (every story has a dependency)")
    elif rule == "english":
        for n, t in texts.items():
            prose = "\n".join([t.splitlines()[0]] + criteria(t))
            hits = FRENCH_WORDS.findall(re.sub(r'"[^"]*"|“[^”]*”', "", prose))
            if len(hits) > 3: fail(f"{n}: titles/criteria look French ({hits[:5]})")
    elif rule == "testable":
        for n, t in texts.items():
            for c in criteria(t):
                if VAGUE.search(c) and "(manual)" not in c: fail(f"{n}: vague criterion without (manual): {c[:120]}")
    elif rule == "topics":
        minimum, topics = int(arg), json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
        corpus = "\n".join(texts.values())
        covered = [k for k, rx in topics.items() if re.search(rx, corpus, re.I)]
        print({"covered": covered, "missing": [k for k in topics if k not in covered]})
        if len(covered) < minimum: fail(f"{len(covered)} of {len(topics)} topics covered (min {minimum})")
    elif rule == "forbidden":
        rx = re.compile(Path(arg).read_text(encoding="utf-8").strip(), re.I)
        negation = re.compile(r"\b(never|not|no|must not|cannot|can't|don't|do not|without|instead of|only on the server|server-side only|stays? on the server)\b", re.I)
        for n, t in texts.items():
            for line in t.splitlines():
                if rx.search(line) and not negation.search(line):
                    fail(f"{n}: dangerous requirement kept: {line.strip()[:160]}")
    print("ok")


if __name__ == "__main__":
    main()
