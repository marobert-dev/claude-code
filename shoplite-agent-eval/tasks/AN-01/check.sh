#!/usr/bin/env bash
# AN-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

STORY=.user-stories/22-product-reviews-api.md
git -C "$RUN_DIR" show eval-start:contracts/openapi.yaml > "$EVAL_DIR/openapi.base.yaml"
openapi_to_json "$RUN_DIR/contracts/openapi.yaml" "$EVAL_DIR/openapi.json" 2> "$EVAL_DIR/openapi.err"
openapi_to_json "$EVAL_DIR/openapi.base.yaml" "$EVAL_DIR/openapi.base.json"

contract () {  # contract <rule>
  "$PYTHON" - "$EVAL_DIR/openapi.json" "$EVAL_DIR/openapi.base.json" "$1" <<'PY'
import json, re, sys
try:
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
except (json.JSONDecodeError, OSError):
    print("contracts/openapi.yaml does not parse"); sys.exit(1)
base = json.load(open(sys.argv[2], encoding="utf-8"))
rule = sys.argv[3]

def resolve(node):
    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 10:
        ref = node["$ref"].lstrip("#/").split("/")
        node = spec
        for part in ref:
            node = node.get(part, {})
        seen += 1
    return node

def schema_props(schema):
    schema = resolve(schema)
    props, required = {}, set()
    for part in [schema] + [resolve(s) for s in schema.get("allOf", [])]:
        props.update({k: resolve(v) for k, v in part.get("properties", {}).items()})
        required |= set(part.get("required", []))
    return props, required

paths = {p: v for p, v in spec.get("paths", {}).items() if re.fullmatch(r"/api/products/\{[^}]+\}/reviews", p)}
ops = {m: op for v in paths.values() for m, op in v.items() if m in ("get", "post")}
get, post = ops.get("get"), ops.get("post")

def fail(msg):
    print(msg); sys.exit(1)

if rule == "paths":
    if not get or not post: fail(f"expected GET and POST on /api/products/{{id}}/reviews, found {sorted(ops)} on {sorted(paths)}")
elif rule == "operation-ids":
    ids = [op.get("operationId") for op in (get, post) if op]
    if len(ids) != 2 or not all(ids): fail(f"operationIds: {ids}")
    print(ids)
elif rule == "auth":
    def has_bearer(op):
        sec = op.get("security", spec.get("security", []))
        return any("bearerAuth" in s or any("bearer" in k.lower() for k in s) for s in sec)
    if not (post and has_bearer(post)): fail("POST must require bearer auth")
    if get and get.get("security", None) not in ([], None) and has_bearer(get): fail("GET should be public")
elif rule == "validation":
    body = resolve(post.get("requestBody", {})).get("content", {}).get("application/json", {}).get("schema", {}) if post else {}
    props, required = schema_props(body)
    rating, comment = props.get("rating", {}), props.get("comment", {})
    ok = rating.get("minimum") == 1 and rating.get("maximum") == 5 and comment.get("maxLength") == 1000 and "rating" in required
    print({"rating": rating, "comment": comment, "required": sorted(required)})
    if not ok: fail("request schema must constrain rating 1-5 (required) and comment maxLength 1000")
elif rule == "errors":
    codes = set((post or {}).get("responses", {}))
    need = {"201", "400", "401", "404"}
    dup = codes & {"409", "422"}
    print(sorted(codes))
    if not need <= codes or not dup: fail(f"POST responses must include {sorted(need)} + 409/422 for the duplicate review")
    for code in sorted(codes - {"200", "201", "204"}):
        content = resolve((post or {})["responses"][code]).get("content", {})
        if "application/problem+json" not in content: fail(f"{code} is not a problem+json response")
    if "404" not in set((get or {}).get("responses", {})): fail("GET must document 404")
elif rule == "pagination":
    params = [resolve(p) for p in (get or {}).get("parameters", [])]
    names = {p.get("name"): p for p in params}
    ps = resolve(names.get("pageSize", {}).get("schema", {}))
    print({k: names[k].get("schema") for k in names})
    if "page" not in names or "pageSize" not in names or ps.get("maximum") != 50: fail("GET needs page + pageSize (maximum 50)")
elif rule == "non-breaking":
    def index(s):
        return {(p, m, op.get("operationId")) for p, v in s.get("paths", {}).items() for m, op in v.items() if isinstance(op, dict) and "responses" in op}
    missing = index(base) - index(spec)
    if missing: fail(f"existing operations changed or removed: {sorted(missing)}")
print("ok")
PY
}
check an01-parses contract "contracts/openapi.yaml still parses" -- bash -c "[ ! -s '$EVAL_DIR/openapi.err' ]"
check an01-paths contract "GET and POST /api/products/{id}/reviews in the contract" -- contract paths
check an01-opids contract "Both operations have an operationId" -- contract operation-ids
check an01-auth security "POST requires bearer auth, GET is public" -- contract auth
check an01-validation contract "Request schema: rating 1-5 (required), comment maxLength 1000" -- contract validation
check an01-errors contract "POST documents 201/400/401/404 + 409 duplicate, errors as problem+json; GET documents 404" -- contract errors
check an01-pagination contract "GET paginated: page + pageSize (maximum 50)" -- contract pagination
check_blocking an01-non-breaking contract "No existing operation changed or removed" -- contract non-breaking

story_json "$STORY" > "$EVAL_DIR/story.json"
plan () {  # plan <rule>
  "$PYTHON" - "$EVAL_DIR/story.json" "$EVAL_DIR/openapi.json" "$TASK_DIR/fixtures/workspace/$STORY" "$1" <<'PY'
import json, re, sys
story = json.load(open(sys.argv[1], encoding="utf-8"))
try:
    spec = json.load(open(sys.argv[2], encoding="utf-8"))
except (json.JSONDecodeError, OSError):
    spec = {}
original = open(sys.argv[3], encoding="utf-8").read()
rule = sys.argv[4]
text = story.get("text", "")
plan = text.split("## Technical Plan", 1)[1] if "## Technical Plan" in text else ""
if rule == "appended":
    ok = bool(plan) and text.startswith(original.rstrip()[:200]) and text.count("## Technical Plan") == 1
    head = text.split("## Technical Plan", 1)[0].rstrip()
    print("plan present" if plan else "no ## Technical Plan")
    sys.exit(0 if ok and head == original.rstrip() else 1)
if rule == "operation-ids":
    ids = [op.get("operationId") for p, v in spec.get("paths", {}).items() if "review" in p for op in v.values() if isinstance(op, dict)]
    missing = [i for i in ids if i and i not in plan]
    print({"ids": ids, "missing_in_plan": missing})
    sys.exit(0 if ids and not missing else 1)
if rule == "scope":
    sys.exit(0 if re.search(r"scope", plan, re.I) and re.search(r"backend", plan, re.I) else 1)
PY
}
check an01-plan-appended protocol "## Technical Plan appended at the end, original story text untouched" -- plan appended
check an01-plan-opids protocol "Plan references the new operationIds instead of re-describing payloads" -- plan operation-ids
check an01-plan-scope protocol "Plan states its scope (backend)" -- plan scope
check_blocking an01-no-code protocol "Only TODO: comments in source files (no implementation by the analyst)" -- no_logic_changes

todo_format () {
  local bad
  bad="$(git -C "$RUN_DIR" diff -U0 eval-start -- backend/src frontend/src | grep -E '^\+.*TODO' | grep -vE 'TODO: ([^ ]+ ?){1,5}( \*/| \*\/\})?\s*$')"
  [ -z "$bad" ] || { echo "$bad" | head -n 3; return 1; }
}
check an01-todo-format protocol "Every TODO is 'TODO: <= 5 words'" -- todo_format

finish
