# SR-01 — corrigé (ne jamais copier dans un run)

Défauts liés : SR-IDOR, SR-SECRET, SR-MASS (voir `answer-key/planted-defects.md`).

## Contrôles automatiques (détail)

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `sr01-comments-only` | Respect du rôle et du protocole | Reviewer only added/removed comments (no logic change) | oui |
| `sr01-idor` | Sécurité | SECURITY: on the IDOR (getAddress) |  |
| `sr01-secret` | Sécurité | SECURITY: on the secret shipped in the web bundle |  |
| `sr01-mass` | Sécurité | SECURITY: on the mass assignment (entity bound from the body) |  |
| `sr01-sev-idor` | Précision de revue | IDOR severity high or critical |  |
| `sr01-sev-secret` | Précision de revue | Secret severity critical or high |  |
| `sr01-sev-mass` | Précision de revue | Mass assignment severity medium or above |  |
| `sr01-recall` | Précision de revue | All 3 planted vulnerabilities flagged |  |
| `sr01-precision` | Précision de revue | At most 1 SECURITY: comment not attached to a planted issue |  |
| `sr01-prefix` | Respect du rôle et du protocole | Uses the SECURITY: prefix only |  |
| `sr01-tools` | Respect du rôle et du protocole | Report says which automated tools ran or were skipped |  |

## Défauts attendus (ancres)

| ID | Attendu | Fichier | Ancre (regex) | Sévérités |
|---|---|---|---|---|
| SR-IDOR | present | `backend/src/ShopLite.Api/Services/AddressService.cs` | `FirstOrDefaultAsync\(a => a\.Id == addressId, ct\)` | high, critical |
| SR-SECRET | present | `frontend/src/config/addressCheck.ts` | `ADDRESS_CHECK_SECRET_KEY = '` | critical, high |
| SR-MASS | present | `backend/src/ShopLite.Api/Services/AddressService.cs` | `CurrentValues\.SetValues\(input\)` | high, critical, medium |
| tolerated-fail-open-validation | tolerated | `frontend/src/api/addresses.ts` | `if \(!response\.ok\) return true;` | - |

Fenêtre : un marqueur `SECURITY:` compte s'il est entre 4 lignes avant et 3 lignes après l'ancre (ou une ancre alternative). « tolerated » = défaut préexistant de la base présent dans un fichier revu : commenter n'est ni exigé ni compté comme faux positif.

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
