#!/usr/bin/env python3
"""Helper commands shared by the kit's bash scripts (standard library only).

Every sub-command prints JSON (or a single word) on stdout so bash can stay thin.
Run `python evalkit.py <command> --help` for the arguments of one command.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

COORDINATION_DIRS = (".user-stories", ".stories-reviewed", ".validated-stories", ".completed", ".decisions", ".pipeline")
COORDINATION_SKIP = re.compile(r"^\.pipeline/team-memory\.db")
HIDDEN_PATHS = ("backend/tests/ShopLite.Api.HiddenTests", "frontend/tests/hidden", "tests/e2e/hidden")
MARKERS = ("REVIEW:", "SECURITY:", "TODO:")
TEST_DIRS = ("backend/tests/", "frontend/tests/", "tests/e2e/")
CS_TEST_CASE = re.compile(r"\[(Fact|Theory)\b")
TS_TEST_CASE = re.compile(r"(?<![\w.])(it|test)(\.each\([^)]*\))?\s*\(")
SKIP_PATTERN = re.compile(r"(\bit\.skip\(|\btest\.skip\(|\bdescribe\.skip\(|\.only\(|Skip\s*=)")
COMMENT_START = re.compile(r"^\s*(//|/\*|\*|#|\{/\*|<!--|-->|\*/)")
TRAILING_COMMENT = re.compile(r"\s*(//|\{/\*).*$")


# ----------------------------------------------------------------------------- small utilities
def out(value) -> None:
    json.dump(value, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def read_json(path: str | Path, default=None):
    p = Path(path)
    if not p.is_file():
        return default
    with p.open(encoding="utf-8") as f:
        text = f.read()
    return json.loads(text) if text.strip() else default


def write_json(path: str | Path, value) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")


def git(run: str, *args: str, env: dict | None = None, check: bool = True) -> str:
    full_env = dict(os.environ, **(env or {}))
    res = subprocess.run(["git", "-C", run, "-c", "core.quotepath=off", *args],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", env=full_env)
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def glob_to_regex(pattern: str) -> re.Pattern:
    i, out_re = 0, ""
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out_re += "(?:.*/)?"
            i += 3
            continue
        if pattern.startswith("**", i):
            out_re += ".*"
            i += 2
            continue
        out_re += {"*": "[^/]*", "?": "[^/]"}.get(c, re.escape(c))
        i += 1
    return re.compile(f"^{out_re}$")


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(glob_to_regex(p).match(path) for p in patterns)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_comment_line(line: str) -> bool:
    return line.strip() == "" or bool(COMMENT_START.match(line))


def strip_trailing_comment(line: str) -> str:
    return TRAILING_COMMENT.sub("", line).strip()


# ----------------------------------------------------------------------------- task.json
def cmd_task_field(a) -> None:
    value = read_json(a.task_json, {})
    for part in a.path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    if value is None:
        print("")
    elif isinstance(value, (dict, list)):
        print(json.dumps(value))
    elif isinstance(value, bool):
        print("true" if value else "false")
    else:
        print(value)


# ----------------------------------------------------------------------------- coordination files
def coordination_files(run: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for d in COORDINATION_DIRS:
        base = run / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file():
                rel = p.relative_to(run).as_posix()
                if not COORDINATION_SKIP.match(rel):
                    files[rel] = sha256(p)
    return files


def cmd_snapshot_coord(a) -> None:
    write_json(a.out, coordination_files(Path(a.run)))


def coord_diff(run: Path, baseline: dict[str, str]) -> dict:
    now = coordination_files(run)
    return {
        "added": sorted(set(now) - set(baseline)),
        "deleted": sorted(set(baseline) - set(now)),
        "modified": sorted(p for p in set(now) & set(baseline) if now[p] != baseline[p]),
    }


def cmd_coord_diff(a) -> None:
    out(coord_diff(Path(a.run), read_json(a.baseline, {})))


# ----------------------------------------------------------------------------- git diff metrics
def staged_view(run: str, meta: str) -> dict:
    """Stage the whole working tree into a private index (never touches the agent's own index)."""
    index_src = Path(run) / git(run, "rev-parse", "--git-path", "index").strip()
    index = Path(meta) / "eval.index"
    if index_src.exists():
        shutil.copyfile(index_src, index)
    elif index.exists():
        index.unlink()
    env = {"GIT_INDEX_FILE": str(index)}
    excludes = [f":(exclude){p}" for p in HIDDEN_PATHS]  # .eval/ is ignored via .git/info/exclude
    git(run, "add", "-A", "--", ".", *excludes, env=env)
    return env


def count_test_cases(text: str, path: str) -> int:
    if path.endswith(".cs"):
        return len(CS_TEST_CASE.findall(text))
    if path.endswith((".ts", ".tsx", ".js")):
        return len(TS_TEST_CASE.findall(text))
    return 0


def diff_metrics(run: str, meta: str, ref: str, task: dict) -> dict:
    env = staged_view(run, meta)
    numstat = git(run, "diff", "--cached", "--numstat", "--no-renames", "--ignore-cr-at-eol", ref, env=env)
    name_status = git(run, "diff", "--cached", "--name-status", "--no-renames", ref, env=env)
    patch = git(run, "diff", "--cached", "-U0", "--no-renames", "--ignore-cr-at-eol", ref, env=env)

    files, added_total, removed_total = [], 0, 0
    status_by_path = {}
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            status_by_path[parts[-1]] = parts[0]
    for line in numstat.splitlines():
        a_, r_, path = line.split("\t", 2)
        added = int(a_) if a_.isdigit() else 0
        removed = int(r_) if r_.isdigit() else 0
        added_total += added
        removed_total += removed
        files.append({"path": path, "added": added, "removed": removed, "status": status_by_path.get(path, "M")})

    markers = {m: {"added": 0, "removed": 0} for m in MARKERS}
    added_lines: dict[str, list[str]] = {}
    removed_lines: dict[str, list[str]] = {}
    current = None
    for line in patch.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            continue
        if line.startswith("--- "):
            continue
        if current is None:
            continue
        if line.startswith("+"):
            added_lines.setdefault(current, []).append(line[1:])
            for m in MARKERS:
                markers[m]["added"] += line.count(m)
        elif line.startswith("-"):
            removed_lines.setdefault(current, []).append(line[1:])
            for m in MARKERS:
                markers[m]["removed"] += line.count(m)

    # Lines whose change is more than adding/removing a comment ("logic" changes).
    logic_changes = []
    for path in sorted(set(added_lines) | set(removed_lines)):
        # Contract and docs edits are judged by scope/role rules, not as "logic".
        if path.startswith(("contracts/", "docs/")) or not path.endswith((".cs", ".ts", ".tsx", ".js", ".css", ".json", ".resx", ".html")):
            continue
        plus = [strip_trailing_comment(l) for l in added_lines.get(path, []) if not is_comment_line(l)]
        minus = [strip_trailing_comment(l) for l in removed_lines.get(path, []) if not is_comment_line(l)]
        remaining_minus = list(minus)
        for p in plus:
            if p in remaining_minus:
                remaining_minus.remove(p)
            elif p:
                logic_changes.append({"path": path, "change": "+", "line": p[:160]})
        for m in remaining_minus:
            if m:
                logic_changes.append({"path": path, "change": "-", "line": m[:160]})

    # Test protection: deleted test files, fewer test cases, newly skipped tests.
    tests = {"deleted_files": [], "reduced_files": [], "skipped_added": []}
    for f in files:
        path = f["path"]
        if not path.startswith(TEST_DIRS):
            continue
        if f["status"] == "D":
            if count_test_cases(git(run, "show", f"{ref}:{path}", check=False), path) > 0:
                tests["deleted_files"].append(path)
            continue
        if f["status"] == "M":
            before = count_test_cases(git(run, "show", f"{ref}:{path}", check=False), path)
            try:
                after = count_test_cases((Path(run) / path).read_text(encoding="utf-8"), path)
            except OSError:
                after = 0
            if after < before:
                tests["reduced_files"].append({"path": path, "before": before, "after": after})
        for line in added_lines.get(path, []):
            if SKIP_PATTERN.search(line):
                tests["skipped_added"].append({"path": path, "line": line.strip()[:160]})

    scope = task.get("scope", {})
    allowed = scope.get("allowed", [])
    forbidden = scope.get("forbidden", [])
    changed_paths = [f["path"] for f in files]
    return {
        "ref": ref,
        "files_changed": len(files),
        "lines_added": added_total,
        "lines_removed": removed_total,
        "files": files,
        "out_of_scope": [p for p in changed_paths if allowed and not matches_any(p, allowed)],
        "forbidden_touched": [p for p in changed_paths if forbidden and matches_any(p, forbidden)],
        "contract_changed": "contracts/openapi.yaml" in changed_paths,
        "markers": markers,
        "logic_changes": logic_changes,
        "tests": tests,
    }


def cmd_diff_metrics(a) -> None:
    out(diff_metrics(a.run, a.meta, a.ref, read_json(a.task_json, {})))


# ----------------------------------------------------------------------------- markers in files
def cmd_find_markers(a) -> None:
    run = Path(a.run)
    found = []
    roots = [run / r for r in a.roots] if a.roots else [run]
    for root in roots:
        candidates = [root] if root.is_file() else root.rglob("*")
        for p in candidates:
            if not p.is_file() or any(part in ("node_modules", "bin", "obj", "dist", ".git") for part in p.parts):
                continue
            if p.suffix not in (".cs", ".ts", ".tsx", ".js", ".css", ".html", ".json", ".resx", ".yaml"):
                continue
            rel = p.relative_to(run).as_posix()
            if rel.startswith(HIDDEN_PATHS):
                continue
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if a.marker in line:
                    found.append({"file": rel, "line": n, "text": line.strip()[:300]})
    out(found)


def cmd_review_score(a) -> None:
    """Match inline markers against planted-defect anchors.

    spec: {"marker": "REVIEW:", "roots": [dirs/files scanned for false positives],
           "defects": [{"id", "file", "anchor" (regex), "alt"?: [{"file", "anchor"}], "expect": "present"|"absent"|"tolerated",
                        "severities"?: [...], "must_mention"?: regex, "window_before"?, "window_after"?}],
           "window_before": 4, "window_after": 3}
    Every marker inside a defect's window covers that defect; any other marker under `roots` is a false positive.
    "tolerated" = a pre-existing defect in a reviewed file: a comment there is neither required nor a false positive.
    """
    run = Path(a.run)
    spec = read_json(a.spec)
    marker = spec["marker"]
    before, after = spec.get("window_before", 4), spec.get("window_after", 3)
    cache: dict[str, list[str]] = {}

    def lines_of(rel):
        if rel not in cache:
            p = run / rel
            cache[rel] = p.read_text(encoding="utf-8", errors="replace").splitlines() if p.exists() else []
        return cache[rel]

    claimed: set[tuple[str, int]] = set()
    defects = []
    for d in spec.get("defects", []):
        wb, wa = d.get("window_before", before), d.get("window_after", after)
        hits: list[tuple[str, int]] = []
        anchor_found = False
        for loc in [{"file": d["file"], "anchor": d["anchor"]}, *d.get("alt", [])]:
            lines = lines_of(loc["file"])
            anchor = re.compile(loc["anchor"])
            anchor_lines = [i for i, l in enumerate(lines) if anchor.search(l)]
            anchor_found = anchor_found or bool(anchor_lines)
            hits += sorted({(loc["file"], j) for i in anchor_lines
                            for j in range(max(0, i - wb), min(len(lines), i + wa + 1)) if marker in lines[j]})
        claimed.update(hits)
        severity_ok = None
        if hits:
            text = " ".join(lines_of(f)[j] for f, j in hits)
            if d.get("severities"):
                sev = re.findall(r"\b(critical|high|medium|low)\b", text, re.I)
                severity_ok = any(s.lower() in d["severities"] for s in sev)
            if d.get("must_mention"):
                mention = bool(re.search(d["must_mention"], text, re.I))
                severity_ok = mention if severity_ok is None else (severity_ok and mention)
        defects.append({"id": d["id"], "file": d["file"], "anchor_found": anchor_found, "flagged": bool(hits),
                        "lines": [f"{f}:{j + 1}" for f, j in hits], "severity_ok": severity_ok,
                        "expect": d.get("expect", "present")})

    exts = (".cs", ".ts", ".tsx", ".js", ".css", ".json", ".resx", ".yaml", ".html")
    scanned = []
    for root in spec.get("roots", []):
        base = run / root
        candidates = [base] if base.is_file() else (base.rglob("*") if base.exists() else [])
        for p in candidates:
            if p.is_file() and p.suffix in exts and not any(x in p.parts for x in ("node_modules", "bin", "obj", "dist", "hidden", "ShopLite.Api.HiddenTests")):
                scanned.append(p.relative_to(run).as_posix())
    all_markers = [(rel, i) for rel in sorted(set(scanned)) for i, l in enumerate(lines_of(rel)) if marker in l]
    false_positives = [{"file": f, "line": i + 1, "text": lines_of(f)[i].strip()[:200]}
                       for f, i in all_markers if (f, i) not in claimed]
    flagged = sum(1 for d in defects if d["flagged"] and d["expect"] == "present")
    expected = sum(1 for d in defects if d["expect"] == "present")
    out({"defects": defects, "flagged": flagged, "expected": expected, "total_markers": len(all_markers),
         "false_positives": false_positives})


# ----------------------------------------------------------------------------- story files
CHECKBOX = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(.+)$")


def cmd_story(a) -> None:
    p = Path(a.path)
    if not p.exists():
        out({"exists": False})
        return
    text = p.read_text(encoding="utf-8", errors="replace")
    sections = re.findall(r"^##\s+(.+?)\s*$", text, re.M)
    criteria, in_ac, last = [], False, None
    for line in text.splitlines():
        if line.startswith("## "):
            in_ac = line.strip().lower().startswith("## acceptance criteria")
            continue
        if not in_ac:
            continue
        m = CHECKBOX.match(line)
        if m:
            last = {"checked": m.group(1).lower() == "x", "text": m.group(2).strip(), "note": ""}
            criteria.append(last)
        elif last is not None and line.strip():
            last["note"] = (last["note"] + " " + line.strip()).strip()
    out({"exists": True, "sections": sections, "criteria": criteria, "lines": len(text.splitlines()), "text": text})


# ----------------------------------------------------------------------------- test result parsers
def summary(tests: dict[str, str]) -> dict:
    return {
        "total": len(tests),
        "passed": sum(1 for s in tests.values() if s == "passed"),
        "failed": sum(1 for s in tests.values() if s == "failed"),
        "tests": tests,
    }


def cmd_parse_trx(a) -> None:
    tests = {}
    for trx in a.files:
        if not Path(trx).exists():
            continue
        root = ET.parse(trx).getroot()
        ns = {"t": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {}
        q = ".//t:UnitTestResult" if ns else ".//UnitTestResult"
        for r in root.findall(q, ns):
            outcome = r.get("outcome", "")
            tests[r.get("testName", "?")] = "passed" if outcome == "Passed" else ("skipped" if outcome == "NotExecuted" else "failed")
    write_json(a.out, summary(tests))


def cmd_parse_vitest(a) -> None:
    data = read_json(a.file, {}) or {}
    tests = {}
    for f in data.get("testResults", []):
        for t in f.get("assertionResults", []):
            name = " ".join([*t.get("ancestorTitles", []), t.get("title", "")]).strip()
            tests[name] = "passed" if t.get("status") == "passed" else ("skipped" if t.get("status") in ("skipped", "pending", "todo") else "failed")
    write_json(a.out, summary(tests))


def cmd_parse_playwright(a) -> None:
    data = read_json(a.file, {}) or {}
    tests = {}

    def walk(suite, prefix):
        title = suite.get("title", "")
        here = [*prefix, title] if title and not title.endswith((".ts", ".js")) else prefix
        for spec in suite.get("specs", []):
            name = " ".join([*here, spec.get("title", "")]).strip()
            statuses = [r.get("status") for t in spec.get("tests", []) for r in t.get("results", [])[-1:]]
            tests[name] = "passed" if statuses and all(s == "passed" for s in statuses) else (
                "skipped" if statuses and all(s == "skipped" for s in statuses) else "failed")
        for child in suite.get("suites", []):
            walk(child, here)

    for s in data.get("suites", []):
        walk(s, [])
    write_json(a.out, summary(tests))


def cmd_test_status(a) -> None:
    """pass if >=1 test matches and all matching passed; fail if any matching failed; missing otherwise."""
    data = read_json(a.summary, {"tests": {}}) or {"tests": {}}
    pattern = re.compile(a.pattern)
    matching = {k: v for k, v in data.get("tests", {}).items() if pattern.search(k)}
    if not matching:
        print("missing")
    elif all(v == "passed" for v in matching.values()):
        print("pass")
    else:
        print("fail")


# ----------------------------------------------------------------------------- checks
def cmd_add_check(a) -> None:
    entry = {"id": a.id, "criterion": a.criterion, "passed": a.passed == "1", "blocking": a.blocking == "1",
             "description": a.description, "detail": a.detail or ""}
    with open(a.checks, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cmd_finish_checks(a) -> None:
    entries = []
    if Path(a.checks).exists():
        with open(a.checks, encoding="utf-8") as f:
            entries = [json.loads(l) for l in f if l.strip()]
    out({"checks": entries})


# ----------------------------------------------------------------------------- claude output
MEMORY_LINE = re.compile(r"Memory:\s*\**\s*(available|unavailable)", re.I)


def cmd_metrics(a) -> None:
    raw = Path(a.claude_output).read_text(encoding="utf-8", errors="replace") if Path(a.claude_output).exists() else ""
    data = {}
    for candidate in (raw.strip(), raw.strip().splitlines()[-1] if raw.strip() else ""):
        try:
            data = json.loads(candidate)
            break
        except (json.JSONDecodeError, IndexError):
            continue
    if isinstance(data, list):  # stream-like array: keep the final result object
        data = next((d for d in reversed(data) if isinstance(d, dict) and d.get("type") == "result"), {})
    report = data.get("result") or ""
    m = MEMORY_LINE.search(report)
    metrics = {
        "agent": a.agent,
        "exit_code": int(a.exit_code),
        "is_error": data.get("is_error"),
        "subtype": data.get("subtype"),
        "num_turns": data.get("num_turns"),
        "total_cost_usd": data.get("total_cost_usd"),
        "duration_ms": data.get("duration_ms"),
        "duration_api_ms": data.get("duration_api_ms"),
        "wall_clock_s": int(a.wall_clock_s),
        "usage": data.get("usage"),
        "model_usage": data.get("modelUsage"),
        "session_id": data.get("session_id"),
        "memory_line": m.group(1).lower() if m else None,
        "claude_version": a.claude_version,
        "agents_sha": a.agents_sha,
        "agent_file_sha256": a.agent_file_sha,
        "started_at": a.started_at,
        "parsed": bool(data),
    }
    write_json(a.out, metrics)
    Path(a.report).write_text(report, encoding="utf-8")


# ----------------------------------------------------------------------------- team-memory seed
def cmd_seed_memory(a) -> None:
    sys.path.insert(0, a.store_dir)
    from store import Store  # type: ignore  # noqa: E402

    seed = read_json(a.seed, {})
    store = Store(path=Path(a.run) / ".pipeline" / "team-memory.db", root=a.run)
    written = 0
    for m in seed.get("memories", []):
        store.remember(**m)
        written += 1
    for d in seed.get("decisions", []):
        store.log_decision(**d)
        written += 1
    out({"seeded": written})


# ----------------------------------------------------------------------------- result
def cmd_compose_result(a) -> None:
    run, meta = Path(a.run), Path(a.meta)
    ev = run / ".eval"
    task = read_json(a.task_json, {})
    run_info = read_json(meta / "run.json", {})
    checks = read_json(ev / "checks.json", {"checks": []}).get("checks", [])
    result = {
        "schema": 1,
        "task": run_info.get("task"),
        "run": run_info.get("run"),
        "run_dir": str(run),
        "agent": task.get("agent"),
        "expected_model": task.get("model"),
        "invocation": task.get("invocation"),
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "created_at": run_info.get("created_at"),
        "kit_sha": run_info.get("kit_sha"),
        "agents_sha": run_info.get("agents_sha"),
        "claude_version": run_info.get("claude_version"),
        "metrics": read_json(ev / "metrics.json", {}),
        "diff": read_json(ev / "diff.json", {}),
        "diff_since_base": read_json(ev / "diff-base.json", {}),
        "coordination": read_json(ev / "coordination.json", {}),
        "gate": read_json(ev / "gate.json", {}),
        "hidden": {k: read_json(ev / f"hidden-{k}.json") for k in ("backend", "frontend", "e2e")},
        "decisions": read_json(ev / "decisions.json", {}),
        "checks": checks,
        "manual": read_json(ev / "manual-scores.json"),
    }
    write_json(ev / "result.json", result)
    out({"result": str(ev / "result.json"), "checks": len(checks),
         "passed": sum(1 for c in checks if c["passed"]), "failed": sum(1 for c in checks if not c["passed"])})


def cmd_decisions(a) -> None:
    run = Path(a.run)
    baseline = read_json(a.baseline, {}) or {}
    entries = {}
    for p in sorted((run / ".decisions").glob("*.md")) if (run / ".decisions").exists() else []:
        text = p.read_text(encoding="utf-8", errors="replace")
        entries[p.name] = len(re.findall(r"^\s*\**Agent:?\**", text, re.M))
    before = baseline.get("entries", {})
    out({"entries": entries, "new_entries": {k: v - before.get(k, 0) for k, v in entries.items() if v - before.get(k, 0) > 0}})


# ----------------------------------------------------------------------------- CLI
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # JSON is redirected to files; never the console code page
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("task-field"); s.add_argument("task_json"); s.add_argument("path"); s.set_defaults(fn=cmd_task_field)
    s = sub.add_parser("snapshot-coord"); s.add_argument("run"); s.add_argument("out"); s.set_defaults(fn=cmd_snapshot_coord)
    s = sub.add_parser("coord-diff"); s.add_argument("run"); s.add_argument("baseline"); s.set_defaults(fn=cmd_coord_diff)
    s = sub.add_parser("diff-metrics"); s.add_argument("run"); s.add_argument("meta"); s.add_argument("ref"); s.add_argument("task_json"); s.set_defaults(fn=cmd_diff_metrics)
    s = sub.add_parser("find-markers"); s.add_argument("run"); s.add_argument("marker"); s.add_argument("roots", nargs="*"); s.set_defaults(fn=cmd_find_markers)
    s = sub.add_parser("review-score"); s.add_argument("run"); s.add_argument("spec"); s.set_defaults(fn=cmd_review_score)
    s = sub.add_parser("story"); s.add_argument("path"); s.set_defaults(fn=cmd_story)
    s = sub.add_parser("parse-trx"); s.add_argument("out"); s.add_argument("files", nargs="*"); s.set_defaults(fn=cmd_parse_trx)
    s = sub.add_parser("parse-vitest"); s.add_argument("file"); s.add_argument("out"); s.set_defaults(fn=cmd_parse_vitest)
    s = sub.add_parser("parse-playwright"); s.add_argument("file"); s.add_argument("out"); s.set_defaults(fn=cmd_parse_playwright)
    s = sub.add_parser("test-status"); s.add_argument("summary"); s.add_argument("pattern"); s.set_defaults(fn=cmd_test_status)
    s = sub.add_parser("add-check")
    for name in ("checks", "id", "criterion", "passed", "blocking", "description"):
        s.add_argument(name)
    s.add_argument("detail", nargs="?", default="")
    s.set_defaults(fn=cmd_add_check)
    s = sub.add_parser("finish-checks"); s.add_argument("checks"); s.set_defaults(fn=cmd_finish_checks)
    s = sub.add_parser("metrics")
    for name in ("claude_output", "out", "report", "agent", "exit_code", "wall_clock_s", "claude_version", "agents_sha", "agent_file_sha", "started_at"):
        s.add_argument(name)
    s.set_defaults(fn=cmd_metrics)
    s = sub.add_parser("seed-memory"); s.add_argument("run"); s.add_argument("seed"); s.add_argument("store_dir"); s.set_defaults(fn=cmd_seed_memory)
    s = sub.add_parser("decisions"); s.add_argument("run"); s.add_argument("baseline"); s.set_defaults(fn=cmd_decisions)
    s = sub.add_parser("compose-result"); s.add_argument("run"); s.add_argument("meta"); s.add_argument("task_json"); s.set_defaults(fn=cmd_compose_result)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
