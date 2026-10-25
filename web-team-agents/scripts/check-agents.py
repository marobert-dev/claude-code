"""Checks the agent definitions in agents/*.md against the rest of the repo; no third-party package needed.

    python scripts/check-agents.py [repo-root]        (exit 1 on any problem)

- frontmatter delimited by --- lines, name = file name, a description;
- every mcp__team-memory__<tool> in tools: exists in mcp/team-memory/server.py, and no agent uses the wildcard
  except product-manager (the wildcard loads every tool schema into each call);
- product-manager's Agent(...) list names existing agents;
- every .claude/hooks/<script> a hook calls ships in hooks/;
- no memory: field (team-memory is the shared memory), subagents keep omitClaudeMd, effort and maxTurns;
- no "---" line in a body (scripts/enable-graphify.sh inserts after the last one).
When PyYAML is importable the frontmatter is also parsed as YAML.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SESSION_AGENTS = {"product-manager", "product-owner"}   # run as the session itself: no omitClaudeMd/effort pins

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def main() -> int:
    server = (ROOT / "mcp" / "team-memory" / "server.py").read_text(encoding="utf-8")
    server_tools = set(re.findall(r"@mcp\.tool\(\)\s*\ndef (\w+)", server))
    files = sorted((ROOT / "agents").glob("*.md"))
    names = {f.stem for f in files}
    problems: list[str] = []

    for f in files:
        text = f.read_text(encoding="utf-8")
        m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
        if not m:
            problems.append(f"{f.name}: no frontmatter")
            continue
        front, body = m.group(1), text[m.end():]
        field = {k: v.strip() for k, v in re.findall(r"^([A-Za-z]+):[ \t]*(.*)$", front, re.M)}

        def bad(msg: str) -> None:
            problems.append(f"{f.name}: {msg}")

        if yaml is not None:
            try:
                yaml.safe_load(front)
            except yaml.YAMLError as e:
                bad(f"frontmatter is not valid YAML ({e})")
        if field.get("name") != f.stem:
            bad(f"name '{field.get('name')}' does not match the file name")
        if not field.get("description"):
            bad("no description")
        if "memory" in field:
            bad("memory: is set (team-memory is the shared memory; agent memory injects MEMORY.md into every call)")
        if f.stem not in SESSION_AGENTS:
            for key in ("omitClaudeMd", "effort", "maxTurns"):
                if key not in field:
                    bad(f"subagent without {key}:")
        tools = [t.strip() for t in re.split(r",(?![^(]*\))", field.get("tools", "")) if t.strip()]
        for t in tools:
            mm = re.fullmatch(r"mcp__team-memory__(.+)", t)
            if mm and mm.group(1) == "*" and f.stem != "product-manager":
                bad("lists mcp__team-memory__* (name the tools it calls instead)")
            elif mm and mm.group(1) != "*" and mm.group(1) not in server_tools:
                bad(f"unknown team-memory tool {mm.group(1)}")
            am = re.fullmatch(r"Agent\((.*)\)", t)
            if am:
                for a in (x.strip() for x in am.group(1).split(",")):
                    if a not in names:
                        bad(f"Agent() lists unknown agent {a}")
        for script in set(re.findall(r"\.claude/hooks/([\w.-]+\.sh)", front)):
            if not (ROOT / "hooks" / script).is_file():
                bad(f"a hook calls .claude/hooks/{script}, which hooks/ does not ship")
        if re.search(r"^---\s*$", body, re.M):
            bad("the body contains a '---' line (enable-graphify inserts its block after the last one)")

    for p in problems:
        print("FAIL", p)
    print(f"{len(files)} agents checked{'' if yaml else ' (YAML not parsed: PyYAML not installed)'}: "
          f"{'all valid' if not problems else f'{len(problems)} problem(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
