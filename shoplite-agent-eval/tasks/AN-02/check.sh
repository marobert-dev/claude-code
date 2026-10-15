#!/usr/bin/env bash
# AN-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

STORY=.user-stories/07-reliable-checkout.md
openapi_to_json "$RUN_DIR/contracts/openapi.yaml" "$EVAL_DIR/openapi.json" 2> "$EVAL_DIR/openapi.err"

todo_in_method () {  # todo_in_method <file> <method-signature regex>
  "$PYTHON" - "$RUN_DIR/$1" "$2" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
start = next((i for i, l in enumerate(lines) if re.search(sys.argv[2], l)), None)
if start is None:
    print("method not found"); sys.exit(1)
end = next((i for i in range(start + 1, len(lines)) if lines[i] == "    }"), len(lines))
todos = [i + 1 for i in range(max(0, start - 3), end + 1) if "TODO:" in lines[i]]
print({"method_lines": (start + 1, end + 1), "todo_lines": todos})
sys.exit(0 if todos else 1)
PY
}
check an02-todo-checkout functional "TODO: inside/above OrderService.CheckoutAsync (stock check + single save)" -- \
  todo_in_method backend/src/ShopLite.Api/Services/OrderService.cs 'Task<OrderDto> CheckoutAsync'
check an02-todo-web functional "TODO: on the web side where checkout errors are shown (409 handling)" -- \
  grep_present 'TODO:' frontend/src/pages/CartPage.tsx frontend/src/api/orders.ts frontend/src/api/client.ts
check an02-todo-resources functional "TODO: where the new localized message goes (resources or Errors/)" -- \
  grep_present 'TODO:' backend/src/ShopLite.Api/Resources backend/src/ShopLite.Api/Errors backend/src/ShopLite.Api/Controllers/OrdersController.cs

contract_409 () {
  "$PYTHON" - "$EVAL_DIR/openapi.json" <<'PY'
import json, sys
try:
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
except (json.JSONDecodeError, OSError):
    print("contract does not parse"); sys.exit(1)
responses = spec.get("paths", {}).get("/api/orders", {}).get("post", {}).get("responses", {})
print(sorted(responses))
sys.exit(0 if "409" in responses or "422" in responses else 1)
PY
}
check an02-contract contract "checkout documents the new refusal (409/422 problem response)" -- contract_409

story_json "$STORY" > "$EVAL_DIR/story.json"
plan_mentions () {  # plan_mentions <regex>
  "$PYTHON" - "$EVAL_DIR/story.json" "$1" <<'PY'
import json, re, sys
text = json.load(open(sys.argv[1], encoding="utf-8")).get("text", "")
plan = text.split("## Technical Plan", 1)[1] if "## Technical Plan" in text else ""
sys.exit(0 if plan and re.search(sys.argv[2], plan, re.I) else 1)
PY
}
check an02-plan-breaking contract "Plan identifies the breaking change for clients (new refusal status on checkout)" -- plan_mentions 'breaking'
check an02-plan-atomic functional "Plan makes the checkout atomic (single unit of work / transaction)" -- plan_mentions 'atomic|transaction|single SaveChanges|unit of work|all-or-nothing'
check an02-plan-stock functional "Plan checks and decrements stock" -- plan_mentions 'stock'
check an02-plan-inmemory functional "Plan notes the InMemory provider limitation on transactions" -- plan_mentions 'InMemory|in-memory'
plan_scope () { plan_mentions 'backend' && plan_mentions 'web|frontend'; }
check an02-plan-scope-both protocol "Plan states both scopes (backend + web)" -- plan_scope
check_blocking an02-no-code protocol "Only TODO: comments in source files (no implementation by the analyst)" -- no_logic_changes

finish
