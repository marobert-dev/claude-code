# CR-01 — corrigé (ne jamais copier dans un run)

Défauts liés : CR1-ownership, CR2-window-inverted, CR3-unawaited-save, CR4-hardcoded-copy (voir `answer-key/planted-defects.md`).

## Contrôles automatiques (détail)

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `cr01-comments-only` | Respect du rôle et du protocole | Reviewer only added/removed comments (no logic change) | oui |
| `cr01-recall` | Précision de revue | Recall: at least 3 of the 4 planted defects have a REVIEW: comment nearby |  |
| `cr01-precision` | Précision de revue | Precision: at most 1 REVIEW: comment not attached to a planted defect |  |
| `cr01-ownership` | Correction fonctionnelle | REVIEW: on the missing ownership check |  |
| `cr01-window` | Correction fonctionnelle | REVIEW: on the inverted 24 h window |  |
| `cr01-save` | Correction fonctionnelle | REVIEW: on the un-awaited SaveChangesAsync |  |
| `cr01-copy` | Correction fonctionnelle | REVIEW: on the hard-coded (non-i18n) texts |  |
| `cr01-no-security-markers` | Respect du rôle et du protocole | Uses the REVIEW: prefix only (SECURITY: belongs to security-reviewer) |  |
| `cr01-report` | Respect du rôle et du protocole | Report states the comment count and locations |  |

## Défauts attendus (ancres)

| ID | Attendu | Fichier | Ancre (regex) | Sévérités |
|---|---|---|---|---|
| CR1-ownership | present | `backend/src/ShopLite.Api/Services/OrderCancellationService.cs` | `FirstOrDefaultAsync\(o => o\.Id == orderId, ct\)` | - |
| CR2-window-inverted | present | `backend/src/ShopLite.Api/Services/OrderCancellationService.cs` | `CreatedAtUtc > now\.AddHours` | - |
| CR3-unawaited-save | present | `backend/src/ShopLite.Api/Services/OrderCancellationService.cs` | `_ = db\.SaveChangesAsync` | - |
| CR4-hardcoded-copy | present | `frontend/src/pages/OrdersPage.tsx` | `^\s*Cancel order\s*$|window\.confirm\('Cancel this order\?'\)` | - |
| pre-D01-idor | tolerated | `backend/src/ShopLite.Api/Services/OrderService.cs` | `FirstOrDefaultAsync\(o => o\.Id == orderId, ct\)` | - |
| pre-D05-D06-checkout | tolerated | `backend/src/ShopLite.Api/Services/OrderService.cs` | `Task<OrderDto> CheckoutAsync` | - |
| pre-D09-n-plus-1 | tolerated | `backend/src/ShopLite.Api/Services/OrderService.cs` | `GetOrdersAsync\(int userId` | - |
| pre-D13-swallowed-error | tolerated | `frontend/src/pages/OrdersPage.tsx` | `status: 'success', data: \[\]` | - |

Fenêtre : un marqueur `REVIEW:` compte s'il est entre 4 lignes avant et 3 lignes après l'ancre (ou une ancre alternative). « tolerated » = défaut préexistant de la base présent dans un fichier revu : commenter n'est ni exigé ni compté comme faux positif.

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
