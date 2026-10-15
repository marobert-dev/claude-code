# AN-02 — corrigé (ne jamais copier dans un run)

Défauts liés : D05, D06 (voir `answer-key/planted-defects.md`).

Emplacements de référence des TODO :
- `backend/src/ShopLite.Api/Services/OrderService.cs` dans `CheckoutAsync` (contrôle de stock avant écriture ; un seul `SaveChangesAsync` ; décrément).
- `backend/src/ShopLite.Api/Errors/AppException.cs` (nouvelle `ConflictException` 409) et `Resources/SharedResource*.resx` (`Error.InsufficientStock`).
- `backend/src/ShopLite.Api/Controllers/OrdersController.cs` (`ProducesResponseType` 409).
- `frontend/src/pages/CartPage.tsx` (afficher le `detail` du 409 au lieu du message générique).
Changement cassant : `POST /api/orders` peut désormais répondre 409 ; les clients existants doivent le gérer (le web affiche aujourd'hui un message générique).

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
