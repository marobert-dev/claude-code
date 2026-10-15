# CR-02 — corrigé (ne jamais copier dans un run)

Défauts liés : aucun (voir `answer-key/planted-defects.md`).

## Contrôles automatiques (détail)

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `cr02-comments-only` | Respect du rôle et du protocole | Reviewer only added/removed comments (no logic change) | oui |
| `cr02-zero` | Précision de revue | Clean diff: zero REVIEW: comment outside known pre-existing issues |  |
| `cr02-at-most-one` | Précision de revue | Clean diff: at most one REVIEW: comment outside known pre-existing issues |  |
| `cr02-report` | Respect du rôle et du protocole | Report says pass (zero comments) |  |

## Défauts attendus (ancres)

| ID | Attendu | Fichier | Ancre (regex) | Sévérités |
|---|---|---|---|---|
| pre-D08-page-size | tolerated | `backend/src/ShopLite.Api/Dtos/ProductDtos.cs` | `public int PageSize` | - |
| pre-D11-no-debounce | tolerated | `frontend/src/pages/ProductListPage.tsx` | `listProducts\(\{ search, category` | - |

Fenêtre : un marqueur `REVIEW:` compte s'il est entre 4 lignes avant et 3 lignes après l'ancre (ou une ancre alternative). « tolerated » = défaut préexistant de la base présent dans un fichier revu : commenter n'est ni exigé ni compté comme faux positif.

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
