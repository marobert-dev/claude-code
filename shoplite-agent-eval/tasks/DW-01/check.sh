#!/usr/bin/env bash
# DW-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

manual_check () {  # manual_check <rule>
  "$PYTHON" - "$RUN_DIR" "$1" <<'PY'
import html, re, sys
from pathlib import Path
run, rule = Path(sys.argv[1]), sys.argv[2]
root = run / "docs" / "user-manual"
pages = {lang: sorted((root / lang).rglob("*.html")) for lang in ("en", "fr")}

def text(p):
    raw = p.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", raw)).replace("’", "'").replace(" ", " ")

def fail(msg):
    print(msg); sys.exit(1)

if rule == "exists":
    if not (run / "docs/dev/README.md").exists(): fail("docs/dev/README.md missing")
    for lang in ("en", "fr"):
        if not (root / lang / "index.html").exists(): fail(f"docs/user-manual/{lang}/index.html missing")
elif rule == "cross-links":
    for lang, other in (("en", "fr"), ("fr", "en")):
        for p in pages[lang]:
            if not re.search(rf'href=["\'](\.\./)+{other}/|href=["\'][^"\']*/{other}/', p.read_text(encoding="utf-8")):
                fail(f"{p.relative_to(run)} has no link to its {other} counterpart")
    if not pages["en"]: fail("no English page")
elif rule == "search":
    for lang in ("en", "fr"):
        idx = (root / lang / "index.html").read_text(encoding="utf-8") if (root / lang / "index.html").exists() else ""
        if not re.search(r'<input[^>]*(type=["\']search["\']|id=["\'][^"\']*search|role=["\']search)', idx, re.I): fail(f"{lang}: no search box")
        if not re.search(r"<script", idx, re.I): fail(f"{lang}: no script for the search")
elif rule == "no-cdn":
    for p in pages["en"] + pages["fr"]:
        s = p.read_text(encoding="utf-8")
        if re.search(r'<script[^>]+src=["\']https?:|<link[^>]+href=["\']https?:', s, re.I): fail(f"external dependency in {p.relative_to(run)}")
elif rule == "no-jargon":
    bad = {"en": r"\b(component|endpoint|API|front-?end|back-?end|database|JSON|HTTP)\b",
           "fr": r"\b(composant|endpoint|API|front-?end|back-?end|base de données|JSON|HTTP|point de terminaison)\b"}
    for lang in ("en", "fr"):
        for p in pages[lang]:
            m = re.search(bad[lang], text(p), re.I)
            if m: fail(f"jargon '{m.group(0)}' in {p.relative_to(run)}")
elif rule == "copy":
    en = " ".join(text(p) for p in pages["en"])
    fr = " ".join(text(p) for p in pages["fr"])
    for needle in ("My orders", "You have no orders yet."):
        if needle not in en: fail(f"EN copy missing: {needle}")
    for needle in ("Mes commandes", "Vous n'avez encore passé aucune commande."):
        if needle not in fr: fail(f"FR copy missing: {needle}")
elif rule == "french-is-french":
    en = " ".join(text(p) for p in pages["en"])
    fr = " ".join(text(p) for p in pages["fr"])
    if en.strip() == fr.strip() or not re.search(r"\b(la|le|les|vous|votre|cliquez|commande)\b", fr, re.I): fail("French manual is not French text")
elif rule == "dev-english":
    s = (run / "docs/dev/README.md").read_text(encoding="utf-8")
    if not re.search(r"\b(the|and|order)\b", s, re.I): fail("developer docs do not look English")
    if "openapi.yaml" not in " ".join(p.read_text(encoding="utf-8") for p in (run / "docs/dev").rglob("*.md")): fail("dev docs do not link contracts/openapi.yaml")
print("ok")
PY
}

check dw01-exists functional "docs/dev/README.md and docs/user-manual/{en,fr}/index.html exist" -- manual_check exists
check dw01-dev-en functional "Developer docs in English and linking contracts/openapi.yaml" -- manual_check dev-english
check dw01-cross-links a11y_i18n "Every manual page links to its other-language counterpart" -- manual_check cross-links
check dw01-search functional "Each language site has a working search box (input + script)" -- manual_check search
check dw01-no-cdn code_quality "No external/CDN dependency in the manual" -- manual_check no-cdn
check dw01-no-jargon a11y_i18n "No technical jargon in the beginner manual (EN and FR)" -- manual_check no-jargon
check dw01-copy a11y_i18n "Exact on-screen copy quoted in each language" -- manual_check copy
check dw01-french a11y_i18n "French manual is written in French" -- manual_check french-is-french
coordination_unmodified () { [ "$(json_get "$EVAL_DIR/coordination.json" 'len(d["modified"])')" = "0" ]; }
check dw01-story-untouched protocol "Story file not modified by doc-writer" -- coordination_unmodified
check dw01-summary protocol "One-line summary names the documentation sets" -- report_mentions 'dev|developer|manual|manuel'

finish
