# Learning memory - schema and design notes

## Tables (`~/.claude/learnings/learnings.db`)

- `projects(id, key UNIQUE, name, root, created_at, last_seen)` - `key` is the normalised `origin` URL (`github.com/owner/repo`, lowercase, no credentials, no `.git`) or `path:<normalised root>` without a remote.
- `learnings` - `scope` global|project (global rows have `project_id NULL`, enforced by a CHECK), `kind` rule|decision|pitfall|preference, `text`, `rationale`, `evidence`, `source` correction|question|error|decision|manual, `confidence`, `status` pending|approved|rejected|deferred|superseded, `claude_md` (wanted in CLAUDE.md), `claude_md_applied` + `applied_file` (what is actually written and where), `supersedes_id`, `fingerprint`. Unique on `(scope, project_id, fingerprint)` across all statuses, so a rejected learning is never proposed again.
- `sessions(session_id, project_id, transcript_path, status queued|analyzing|done|failed|skipped, attempts, analyzed_bytes, ...)` - `analyzed_bytes` makes a resumed session analyse only the new part of its transcript.
- `meta(key, value)` - `installed_at` bounds the sweep so old transcripts are never back-filled.

## Flow and guards

- Loop guard: the analyzer's own `claude -p` runs with env `CLAUDE_LEARN_ANALYZER=1`; every hook subcommand exits immediately when it is set, so analysing never triggers capture or load.
- SessionEnd budget is short (1.5 s default): `capture` only writes one row and spawns a detached process.
- Hooks never fail a session: any exception is logged and the exit code stays 0.
- The analyzer prompt is `prompts/extract.md`. The digest drops sidechain/meta messages, system reminders and command echoes, redacts common secret patterns, and is capped at `max_digest_chars` (assistant text is dropped first).
- Retries: failed sessions are retried by the next sweep up to `max_attempts`. A session stuck in `analyzing` for 30 minutes is retried.
- `SessionStart` injects approved learnings minus those already in CLAUDE.md; `SubagentStart` injects all approved ones within a smaller budget (subagents often skip CLAUDE.md).

## CLAUDE.md managed block

```
<!-- learnings:start (managed by /learn-review; lines are tracked by id) -->
## Learned rules
- Run gate.sh before any commit. <!-- L12 -->
<!-- learnings:end -->
```

Lines are matched by the `<!-- L<id> -->` marker. Editing a line's wording by hand is safe; deleting a line by hand makes the database think it is still applied until the learning is forgotten. The block is removed when its last line goes.

## Markdown export format (`export` / `import`)

One file per scope: `global.md` and `projects/<name>-<hash6 of project key>.md`, plus `INDEX.md` (file list, counts, usage). Files carry no timestamp, so re-exporting an unchanged database changes nothing.

```
---
learnings_export: 1
scope: project            # or global (no project_* lines)
project_key: github.com/owner/repo
project_name: repo
project_root: C:/Dev/repo
count: 3
---
# Learnings - repo
## Approved (2)
### #12
- kind: rule
- status: approved
- confidence: high
- source: correction
- claude_md: yes
- applied: no
- supersedes:
- created: 2026-11-05T12:00:00Z
- reviewed: 2026-11-05T13:00:00Z
- session: <session id>
- text: Run gate.sh before any commit.
- rationale: Forgotten twice.
- evidence: you forgot again
```

Sections are ordered approved, pending, deferred, superseded, rejected. `import` reads any `.md` that starts with the front matter (other markdown is ignored), tolerates hand edits of `status`, `text`, `claude_md`, skips invalid entries with `file:line` messages (exit 1), and skips learnings already present (same scope, project and normalised text). Ids are kept when free, otherwise remapped, and `supersedes` links follow the remap. `applied` is reset to `no` unless `--keep-applied`, because the CLAUDE.md files may not exist on the target machine; run `claude-md plan` afterwards. Sessions and the analysis queue are not exported: on a fresh database old transcripts are never re-analysed.
