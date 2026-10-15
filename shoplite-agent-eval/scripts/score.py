#!/usr/bin/env python3
"""Aggregate run results into scores, verdicts and the evaluation-sheet table (standard library only).

Usage:
  python scripts/score.py BE-02                 # task BE-02, runs 1..3 found under $EVAL_RUNS_DIR
  python scripts/score.py BE-02 --runs 1,2,3,4  # explicit runs
  python scripts/score.py --all                 # every task that has at least one checked run
  python scripts/score.py --all --update-sheet  # also rewrite the recap table in docs/evaluation-sheet.md
  python scripts/score.py BE-02 --json out.json # machine-readable summary

Scoring (docs/scoring-criteria.md): each applicable criterion gets 0/1/2 points per run;
score = sum(points) / (2 x number of scored criteria) x 100; PASS >= 80, BORDERLINE 65-79, FAIL < 65;
any blocking failure makes the run FAIL whatever its score. A task PASSes when >= 2 runs PASS and no run
has a blocking failure. Criteria with no measurement (manual criterion not filled in) are left out and the
run is flagged "provisional".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
RUNS_DIR = Path(os.environ.get("EVAL_RUNS_DIR", Path.home() / "shoplite-runs"))
SHEET = KIT / "docs" / "evaluation-sheet.md"
PASS_THRESHOLD, BORDERLINE_THRESHOLD = 80.0, 65.0
MAJOR_OUT_OF_SCOPE_FILES = 5
MAJOR_DIFF_FACTOR = 2
CRITERIA_ORDER = ["gate_tests", "functional", "scope", "protocol", "contract", "security", "code_quality",
                  "tests_quality", "review_precision", "a11y_i18n", "performance", "efficiency", "stability"]
SHEET_BEGIN, SHEET_END = "<!-- score:begin -->", "<!-- score:end -->"


def read_json(path: Path, default=None):
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text) if text.strip() else default
    except (OSError, json.JSONDecodeError):
        return default


def ratio_points(passed: int, total: int) -> int:
    if total == 0:
        return -1
    ratio = passed / total
    return 2 if ratio == 1 else (1 if ratio >= 0.5 else 0)


def efficiency_points(metrics: dict, budgets: dict) -> int:
    if not metrics or not metrics.get("parsed"):
        return -1
    duration = (metrics.get("duration_ms") or 0) / 1000 or metrics.get("wall_clock_s") or 0
    measured = {"turns": metrics.get("num_turns"), "cost_usd": metrics.get("total_cost_usd"), "duration_s": duration}
    exceeded = sum(1 for k, limit in budgets.items() if measured.get(k) is not None and limit and float(measured[k]) > float(limit))
    return 2 if exceeded == 0 else (1 if exceeded == 1 else 0)


def gate_points(result: dict) -> int:
    if not (result.get("gate") or {}).get("passed"):
        return 0
    suites = [s for s in (result.get("hidden") or {}).values() if s]
    if not suites:
        return 2
    return 2 if all(s.get("failed", 1) == 0 and s.get("total", 0) > 0 for s in suites) else 1


def score_run(task: dict, result: dict) -> dict:
    checks = result.get("checks", [])
    manual = result.get("manual") or {}
    applicable = [c for c in task.get("criteria", []) if c != "stability"]
    points, notes = {}, []
    for criterion in applicable:
        if criterion == "gate_tests":
            points[criterion] = gate_points(result)
        elif criterion == "efficiency":
            points[criterion] = efficiency_points(result.get("metrics") or {}, task.get("budgets", {}))
        elif criterion in task.get("manual_criteria", []):
            value = manual.get(criterion)
            points[criterion] = int(value) if isinstance(value, (int, float)) else -1
        else:
            relevant = [c for c in checks if c.get("criterion") == criterion]
            points[criterion] = ratio_points(sum(c["passed"] for c in relevant), len(relevant))
            if criterion in manual and isinstance(manual[criterion], (int, float)):
                points[criterion] = int(manual[criterion])  # an evaluator may overrule an automated score
    scored = {k: v for k, v in points.items() if v >= 0}
    missing = sorted(k for k, v in points.items() if v < 0)
    score = round(sum(scored.values()) / (2 * len(scored)) * 100, 1) if scored else 0.0

    blocking = [f"{c['id']}: {c['description']}" for c in checks if c.get("blocking") and not c.get("passed")]
    diff = result.get("diff") or {}
    max_diff = (task.get("scope") or {}).get("max_diff_lines")
    if len(diff.get("out_of_scope", [])) > MAJOR_OUT_OF_SCOPE_FILES:
        blocking.append(f"major out-of-scope change ({len(diff['out_of_scope'])} files)")
    if max_diff and (diff.get("lines_added", 0) + diff.get("lines_removed", 0)) > MAJOR_DIFF_FACTOR * max_diff:
        blocking.append("major out-of-scope change (diff more than twice the task maximum)")
    if manual.get("blocking"):
        blocking.append(f"manual: {manual['blocking']}")

    if blocking:
        verdict = "FAIL"
    elif score >= PASS_THRESHOLD:
        verdict = "PASS"
    elif score >= BORDERLINE_THRESHOLD:
        verdict = "BORDERLINE"
    else:
        verdict = "FAIL"
    if missing:
        notes.append("provisional: not scored " + ", ".join(missing))
    return {"points": points, "score": score, "verdict": verdict, "blocking": blocking, "notes": notes}


def run_row(task_id: str, run: int, task: dict, result: dict | None, scored: dict | None) -> dict:
    if not result:
        return {"task": task_id, "agent": task.get("agent", ""), "run": run, "present": False}
    metrics = result.get("metrics") or {}
    diff = result.get("diff") or {}
    hidden = [s for s in (result.get("hidden") or {}).values() if s]
    markers = diff.get("markers", {})
    decisions = sum((result.get("decisions") or {}).get("new_entries", {}).values())
    duration = (metrics.get("duration_ms") or 0) / 1000 or metrics.get("wall_clock_s")
    return {
        "task": task_id, "agent": task.get("agent", ""), "run": run, "present": True,
        "gate": "green" if (result.get("gate") or {}).get("passed") else "red",
        "hidden": f"{sum(s.get('passed', 0) for s in hidden)}/{sum(s.get('total', 0) for s in hidden)}" if hidden else "-",
        "score": scored["score"], "verdict": scored["verdict"], "blocking": len(scored["blocking"]),
        "turns": metrics.get("num_turns"), "cost": metrics.get("total_cost_usd"),
        "duration": round(duration) if duration else None,
        "files": diff.get("files_changed"), "plus": diff.get("lines_added"), "minus": diff.get("lines_removed"),
        "out_of_scope": len(diff.get("out_of_scope", [])),
        "markers": "/".join(str(markers.get(m, {}).get("added", 0)) for m in ("TODO:", "REVIEW:", "SECURITY:")),
        "decisions": decisions, "memory": metrics.get("memory_line") or "-",
        "points": scored["points"], "notes": scored["notes"], "blocking_list": scored["blocking"],
        "agents_sha": result.get("agents_sha"), "claude_version": result.get("claude_version"),
    }


def score_task(task_id: str, runs: list[int]) -> dict:
    task = read_json(KIT / "tasks" / task_id / "task.json", {}) or {}
    rows = []
    for n in runs:
        result = read_json(RUNS_DIR / f"{task_id}-run{n}" / ".eval" / "result.json")
        scored = score_run(task, result) if result else None
        rows.append(run_row(task_id, n, task, result, scored))
    present = [r for r in rows if r["present"]]
    verdicts = [r["verdict"] for r in present]
    any_blocking = any(r["blocking"] for r in present)
    passes = verdicts.count("PASS")
    if len(present) >= 2 and passes >= 2 and not any_blocking:
        task_verdict = "PASS"
    elif present and not any_blocking and passes + verdicts.count("BORDERLINE") >= min(2, len(present)):
        task_verdict = "BORDERLINE"
    else:
        task_verdict = "FAIL" if present else "NOT RUN"
    stability = None
    if "stability" in task.get("criteria", []) and len(present) >= 2:
        top = max(verdicts.count(v) for v in set(verdicts))
        stability = 2 if top == len(present) else (1 if top >= 2 else 0)
    scores = [r["score"] for r in present]
    return {
        "task": task_id, "title": task.get("title", ""), "agent": task.get("agent", ""), "model": task.get("model", ""),
        "runs": rows, "verdict": task_verdict, "mean_score": round(statistics.mean(scores), 1) if scores else None,
        "score_stdev": round(statistics.pstdev(scores), 1) if len(scores) > 1 else None,
        "stability": stability, "complete": len(present) >= 3,
    }


def fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.2f}" if v < 100 else f"{v:.0f}"
    return str(v)


ROW_HEADER = ("| Task | Agent | Run | Gate | Hidden | Score % | Verdict | Blocking | Turns | Cost $ | Duration s "
              "| Files | +/- | Out of scope | TODO/REVIEW/SECURITY | .decisions | Memory |")
ROW_SEPARATOR = "|" + "---|" * 17


def row_line(r: dict) -> str:
    if not r["present"]:
        return f"| {r['task']} | {r['agent']} | {r['run']} | | | | | | | | | | | | | | |"
    return (f"| {r['task']} | {r['agent']} | {r['run']} | {r['gate']} | {r['hidden']} | {fmt(r['score'])} | {r['verdict']} "
            f"| {r['blocking']} | {fmt(r['turns'])} | {fmt(r['cost'])} | {fmt(r['duration'])} | {fmt(r['files'])} "
            f"| +{fmt(r['plus'])}/-{fmt(r['minus'])} | {r['out_of_scope']} | {r['markers']} | {r['decisions']} | {r['memory']} |")


def print_task(summary: dict) -> None:
    print(f"\n## {summary['task']} — {summary['title']} ({summary['agent']}, {summary['model']})")
    print(ROW_HEADER)
    print(ROW_SEPARATOR)
    for r in summary["runs"]:
        print(row_line(r))
    present = [r for r in summary["runs"] if r["present"]]
    if present:
        criteria = [c for c in CRITERIA_ORDER if any(c in r["points"] for r in present)]
        print("\n| Criterion | " + " | ".join(f"run {r['run']}" for r in present) + " |")
        print("|---|" + "---|" * len(present))
        for c in criteria:
            cells = [("n/a" if r["points"].get(c, -1) < 0 else str(r["points"][c])) for r in present]
            print(f"| {c} | " + " | ".join(cells) + " |")
        if summary["stability"] is not None:
            print(f"| stability (task) | {summary['stability']} |" + " |" * (len(present) - 1))
        for r in present:
            for b in r["blocking_list"]:
                print(f"- run {r['run']} BLOCKING: {b}")
            for n in r["notes"]:
                print(f"- run {r['run']}: {n}")
    print(f"\n**Task verdict: {summary['verdict']}** — mean score {fmt(summary['mean_score'])} %"
          f" (stdev {fmt(summary['score_stdev'])}), stability {fmt(summary['stability'])}"
          + ("" if summary["complete"] else " — fewer than 3 runs, validation incomplete"))


def update_sheet(summaries: list[dict]) -> None:
    text = SHEET.read_text(encoding="utf-8")
    if SHEET_BEGIN not in text or SHEET_END not in text:
        sys.exit(f"{SHEET} has no {SHEET_BEGIN} / {SHEET_END} markers")
    by_key = {(r["task"], r["run"]): r for s in summaries for r in s["runs"] if r["present"]}
    head, rest = text.split(SHEET_BEGIN, 1)
    body, tail = rest.split(SHEET_END, 1)
    lines = []
    for line in body.strip("\n").splitlines():
        m = re.match(r"^\|\s*([A-Z]+-\d+)\s*\|[^|]*\|\s*(\d+)\s*\|", line)
        if m and (m.group(1), int(m.group(2))) in by_key:
            lines.append(row_line(by_key.pop((m.group(1), int(m.group(2))))))
        else:
            lines.append(line)
    lines += [row_line(r) for r in by_key.values()]
    verdict_lines = [f"| {s['task']} | {s['agent']} | {fmt(s['mean_score'])} | {fmt(s['stability'])} | {s['verdict']} |"
                     for s in summaries]
    new_body = "\n".join(lines)
    tail = re.sub(r"(<!-- verdicts:begin -->\n).*?(\n<!-- verdicts:end -->)",
                  lambda m: m.group(1) + "| Task | Agent | Mean score % | Stability | Task verdict |\n|---|---|---|---|---|\n"
                  + "\n".join(verdict_lines) + m.group(2), tail, flags=re.S)
    SHEET.write_text(f"{head}{SHEET_BEGIN}\n{new_body}\n{SHEET_END}{tail}", encoding="utf-8", newline="\n")
    print(f"updated {SHEET}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", nargs="?", help="task id, e.g. BE-02")
    parser.add_argument("--all", action="store_true", help="score every task that has results")
    parser.add_argument("--runs", default="1,2,3", help="comma-separated run numbers (default 1,2,3)")
    parser.add_argument("--json", help="write the summary as JSON to this file")
    parser.add_argument("--update-sheet", action="store_true", help="rewrite the recap table of docs/evaluation-sheet.md")
    args = parser.parse_args()
    runs = [int(x) for x in args.runs.split(",") if x.strip()]
    if args.all:
        task_ids = sorted(p.name for p in (KIT / "tasks").iterdir() if (p / "task.json").exists())
    elif args.task:
        task_ids = [args.task]
    else:
        parser.error("give a task id or --all")
    summaries = [score_task(t, runs) for t in task_ids]
    if args.all:
        summaries = [s for s in summaries if any(r["present"] for r in s["runs"])] or summaries
    for s in summaries:
        print_task(s)
    if args.json:
        Path(args.json).write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.update_sheet:
        update_sheet(summaries)


if __name__ == "__main__":
    main()
