#!/usr/bin/env bash
# UT-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
# Objective test quality = mutation score: each mutant of ProductService.cs is run against the agent's NEW test classes only.
. "$KIT/scripts/lib/check-lib.sh"

NEW_CLASSES_FILE="$EVAL_DIR/ut01-classes.txt"
git -C "$RUN_DIR" ls-files --others --exclude-standard -- backend/tests/ShopLite.Api.Tests | grep '\.cs$' > "$EVAL_DIR/ut01-new-files.txt"
git -C "$RUN_DIR" diff --name-only --diff-filter=A eval-start -- backend/tests/ShopLite.Api.Tests | grep '\.cs$' >> "$EVAL_DIR/ut01-new-files.txt"
: > "$NEW_CLASSES_FILE"
while read -r f; do
  [ -n "$f" ] && grep -oE 'class [A-Za-z0-9_]+' "$RUN_DIR/$f" | awk '{print $2}' >> "$NEW_CLASSES_FILE"
done < <(sort -u "$EVAL_DIR/ut01-new-files.txt")
FILTER="$(sort -u "$NEW_CLASSES_FILE" | sed 's/^/FullyQualifiedName~./' | paste -sd'|' -)"

has_new_tests () { [ -n "$FILTER" ] || { echo "no new test class under backend/tests/ShopLite.Api.Tests"; return 1; }; }
check ut01-new-tests functional "New unit-test classes added" -- has_new_tests
check ut01-direct tests_quality "Tests exercise ProductService directly (not only HTTP)" -- \
  bash -c "sort -u '$EVAL_DIR/ut01-new-files.txt' | xargs -r grep -l 'new ProductService(' | grep -q ."

run_new_tests () { (cd "$RUN_DIR" && dotnet test backend/tests/ShopLite.Api.Tests --nologo -v q --filter "$FILTER" > /dev/null 2>&1); }
stable_three_times () {
  has_new_tests || return 1
  local i; for i in 1 2 3; do run_new_tests || { echo "run $i failed"; return 1; }; done
}
check ut01-deterministic tests_quality "New tests pass 3 runs in a row" -- stable_three_times
check ut01-no-time-or-random tests_quality "No sleeps, wall clock or randomness in new tests" -- \
  bash -c "! sort -u '$EVAL_DIR/ut01-new-files.txt' | xargs -r grep -nE 'Thread\.Sleep|Task\.Delay|DateTime\.(Now|UtcNow)|new Random\('"

check ut01-src-untouched protocol "Production code untouched (tests only)" -- paths_unchanged backend/src

mutation_run () {
  has_new_tests || return 1
  "$PYTHON" - "$RUN_DIR" "$TASK_DIR/mutants.json" "$FILTER" "$EVAL_DIR/ut01-mutation.json" <<'PY'
import json, subprocess, sys, pathlib
run, spec_path, flt, out = sys.argv[1:]
spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
target = pathlib.Path(run) / spec["file"]
original_bytes = target.read_bytes()  # restored byte for byte (no line-ending conversion)
original = original_bytes.decode("utf-8")
results = []
try:
    for m in spec["mutants"]:
        mutated = original
        applicable = True
        for old, new in m["replace"]:
            if old not in mutated:
                applicable = False
                break
            mutated = mutated.replace(old, new)
        if not applicable:
            results.append({"id": m["id"], "status": "not-applicable"})
            continue
        target.write_bytes(mutated.encode("utf-8"))
        rc = subprocess.run(["dotnet", "test", "backend/tests/ShopLite.Api.Tests", "--nologo", "-v", "q", "--filter", flt],
                            cwd=run, capture_output=True, text=True).returncode
        results.append({"id": m["id"], "status": "killed" if rc != 0 else "survived"})
finally:
    target.write_bytes(original_bytes)
killed = sum(r["status"] == "killed" for r in results)
pathlib.Path(out).write_text(json.dumps({"killed": killed, "total": len(results), "mutants": results}, indent=2), encoding="utf-8")
print(json.dumps(results))
PY
}
mutation_run > "$EVAL_DIR/ut01-mutation.log" 2>&1
killed_at_least () {
  [ -f "$EVAL_DIR/ut01-mutation.json" ] || { echo "mutation run did not complete"; return 1; }
  local k; k="$(json_get "$EVAL_DIR/ut01-mutation.json" 'd["killed"]')"
  echo "killed $k of $(json_get "$EVAL_DIR/ut01-mutation.json" 'd["total"]') mutants"
  [ "$k" -ge "$1" ]
}
check ut01-mutation-high tests_quality "Mutation score: at least 5 of 6 mutants killed" -- killed_at_least 5
check ut01-mutation-medium tests_quality "Mutation score: at least 3 of 6 mutants killed" -- killed_at_least 3

finish
