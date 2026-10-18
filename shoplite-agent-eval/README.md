# ShopLite — kit d'évaluation des sous-agents `web-team-agents`

Ce kit fournit une application cible réaliste (ShopLite : .NET 10 + React), 30 tâches d'évaluation, des fixtures,
des tests cachés et une grille de notation pour mesurer **objectivement et de façon reproductible** les 12
sous-agents Claude Code du dépôt `web-team-agents`. Il ne crée ni ne modifie aucun agent.

Principe : **ce que l'agent voit est séparé de ce qui le note.** Seul `app-template/` (+ les fixtures de la tâche)
est copié dans un run, hors du kit ; le corrigé (`answer-key/`, `tasks/*/expected.md`, `hidden-tests/`, specs de
revue) ne quitte jamais le kit et les tests cachés ne sont copiés qu'**après** l'agent.

```text
shoplite-agent-eval/
├── README.md
├── app-template/          # racine de workspace vue par les agents (aucune mention d'évaluation)
├── tasks/<TASK-ID>/       # task.md, prompt.txt, fixtures/, hidden-tests/, expected.md, check.sh (+ task.json)
│   └── _shared/           # projet xUnit caché, helpers Vitest cachés, contrôles product-owner
├── answer-key/planted-defects.md
├── fixtures/conventions.golden.md
├── scripts/               # new-run.sh, run-agent.sh, check-run.sh, score.py (+ lib/, tools/)
└── docs/                  # recommended-test-suite.md, scoring-criteria.md, evaluation-sheet.md
```

## 1. Prérequis

| Outil | Version testée | Remarque |
|---|---|---|
| Claude Code | 2.1.299 | `claude --version` ; options utilisées : `-p`, `--agent`, `--output-format json`, `--permission-mode acceptEdits`, `--allowedTools`, `--no-session-persistence` |
| .NET SDK | 10.0.402 | `dotnet --list-sdks` doit afficher `10.0.x`. Un SDK installé dans `~/.dotnet` (script `dotnet-install`) est pris en priorité par les scripts du kit ; dans votre terminal, placez-le en tête du `PATH` (un hôte `C:\Program Files\dotnet` sans SDK masquerait sinon le SDK). |
| Node.js / npm | 24.16 / 12.0 | |
| Python | 3.10+ (testé 3.14) | standard library uniquement |
| Git Bash (ou WSL) | 2.55 | tous les scripts sont en bash, comme le pipeline |
| jq | 1.8 | **requis** par `gate.sh` (sans jq, les étapes npm du gate sont ignorées silencieusement) |
| Playwright Chromium | 1.64 | `npx playwright install chromium` (une fois) |

Une fois, depuis la racine du kit :

```bash
npm --prefix scripts/tools install      # convertisseur YAML -> JSON utilisé par les contrôles AN-*
(cd app-template && npm install && npm --prefix frontend install && npx playwright install chromium)
dotnet restore app-template/backend/ShopLite.sln
```

## 2. Installer les agents évalués

```bash
bash ../web-team-agents/install.sh    # copie agents/*.md vers ~/.claude/agents/ (global)
```

Optionnel mais nécessaire pour noter la ligne `Memory: available` et pour ADV-02 : le serveur MCP `team-memory`
installé et enregistré en portée utilisateur (`web-team-agents/mcp/team-memory/README.md`). `new-run.sh` utilise
`store.py` de `TEAM_MEMORY_SRC` (défaut `~/.mcp/team-memory`) pour pré-remplir la mémoire d'une tâche.

Variables reconnues : `EVAL_RUNS_DIR` (défaut `~/shoplite-runs`), `WEB_TEAM_AGENTS_DIR` (défaut `../web-team-agents`),
`TEAM_MEMORY_SRC`, `EVAL_ALLOWED_TOOLS`, `EVAL_CLAUDE_FLAGS`, `EVAL_TIMEOUT`, `EVAL_SKIP_GATE`.

## 3. Lancer l'application ShopLite

Voir `app-template/README.md`. En bref, depuis `app-template/` (ou un run) :

```bash
dotnet run --project backend/src/ShopLite.Api          # API http://localhost:5080 (OpenAPI : /openapi/v1.json)
npm --prefix frontend run dev                          # web http://localhost:5173 (proxy /api)
bash .claude/hooks/gate.sh                             # gate : lint, typecheck, build, Vitest, dotnet build/test
(cd frontend && npm test) ; (cd backend && dotnet test ShopLite.sln)   # tests unitaires
npx playwright test                                    # e2e FR + EN (démarre API et web)
```

Comptes de démonstration : `alice` / `Alice123!`, `bob` / `Bob123!` (clients), `admin` / `Admin123!`.

## 4. Exécuter une tâche de bout en bout

```bash
cd shoplite-agent-eval
RUN=$(bash scripts/new-run.sh BE-02 1)            # copie isolée + git (tags eval-base / eval-start) + fixtures + npm ci
bash scripts/run-agent.sh "$RUN"                   # claude -p "$(cat tasks/BE-02/prompt.txt)" --agent dev-backend …
bash scripts/check-run.sh "$RUN"                   # diff, gate, tests cachés, check.sh -> $RUN/.eval/result.json
python scripts/score.py BE-02 --runs 1             # score par critère + verdict
```

- `run-agent.sh <run> --dry-run` affiche la commande `claude` exacte sans l'exécuter.
- Notes manuelles (qualité du code…) : `$RUN/.eval/manual-scores.json`, par ex. `{"code_quality": 2, "notes": "…"}`, puis relancer `score.py`.
- Les métadonnées d'évaluation (baselines, sortie brute de l'agent) sont dans `$EVAL_RUNS_DIR/.meta/<run>/`, hors du run.

## 5. Campagne complète (3 runs par tâche, team-memory réinitialisée à chaque run)

```bash
for task in $(ls tasks | grep -v '^_'); do
  for n in 1 2 3; do
    RUN=$(bash scripts/new-run.sh "$task" "$n" --force)
    bash scripts/run-agent.sh "$RUN" || echo "agent exit $? on $task run $n"
    bash scripts/check-run.sh "$RUN"
  done
done
python scripts/score.py --all --update-sheet --json campaign.score.json
```

Les runs e2e utilisent les ports 5080/5173 : exécutez les tâches **séquentiellement** (ou fixez
`SHOPLITE_API_PORT` / `SHOPLITE_WEB_PORT` différents par run). Les tâches PM-01/PM-02 sont longues
(budget indicatif 90 min, 25 $ chacune).

## 6. Les 30 tâches

| Agent | Tâches |
|---|---|
| conventions-scout | CS-01 |
| product-owner | PO-01 (requête floue « avis produits »), PO-02 (clé Stripe secrète dans le front) |
| analyst | AN-01 (contrat d'abord, API d'avis), AN-02 (checkout atomique, TODO, changement cassant) |
| dev-backend | BE-01 (validation), BE-02 (IDOR + fuite d'erreurs), BE-03 (rôle admin), BE-04 (checkout atomique + stock), BE-05 (N+1), BE-06 (refactoring) |
| dev-frontend | FE-01 (total arrondi), FE-02 (debounce), FE-03 (modale accessible), FE-04 (états de l'historique), FE-05 (nouvel écran, client stubbé) |
| dev-integrator | DI-01 (stub → appel réel), DI-02 (écart de contrat champ + code HTTP) |
| code-reviewer | CR-01 (4 défauts plantés), CR-02 (diff propre) |
| security-reviewer | SR-01 (IDOR + secret + mass assignment), SR-02 (re-revue après correction partielle) |
| unit-tester | UT-01 (couverture de `ProductService`, score de mutation) |
| story-validator | SV-01 (critère réellement en échec), SV-02 (régression d'une story validée) |
| doc-writer | DW-01 |
| product-manager | PM-01 (`ONE STORY MODE`, COMPLETED), PM-02 (critères contradictoires, arrêt immédiat FAILED) |
| adversarial | ADV-01 (dev-frontend, clé secrète exigée), ADV-02 (dev-backend, mémoire empoisonnée) |

Chaque `tasks/<ID>/task.md` décrit la demande exacte, les fixtures, le résultat attendu, les tests, les critères de
réussite/échec et le périmètre. La notation est décrite dans `docs/scoring-criteria.md`, la suite de tests dans
`docs/recommended-test-suite.md`, la fiche dans `docs/evaluation-sheet.md`.

## 7. Limites connues

- **Isolation imparfaite** : un agent peut lire hors de son run avec Bash/Read. Le kit ne copie jamais son chemin dans
  le run, mais ne peut pas empêcher une exploration du disque. Pour une isolation stricte, exécutez les runs dans un
  conteneur ou une session utilisateur sans accès au dossier du kit.
- **Configuration utilisateur** : `~/.claude/CLAUDE.md`, les skills et les plugins de l'utilisateur sont chargés par
  `claude -p` et influencent les agents évalués. Comparez toujours des campagnes lancées avec la même configuration
  (ou passez des options via `EVAL_CLAUDE_FLAGS`).
- **Gate** : `.claude/hooks/gate.sh` est la copie exacte de `web-team-agents/hooks/gate.sh`. Sa détection .NET
  (`ls "$d"/*.sln "$d"/*.csproj`) échoue quand un dossier contient un `.sln` sans `.csproj` (cas de `backend/`) et
  ignorerait silencieusement `dotnet build/test` ; le template fournit donc `.claude/gate.local.sh`, mécanisme
  d'override prévu par le gate. Le hook `SubagentStop` de `.claude/settings.json` ne se déclenche que pour des
  sous-agents (PM-01/PM-02), pas pour un agent lancé directement avec `--agent` ; `check-run.sh` exécute donc
  toujours le gate lui-même.
- **Budgets d'efficacité** : seuils initiaux à recalibrer après une première campagne.


## Le principe

Pour chaque tâche (BE-02, FE-01, CR-01…), il y a 4 étapes, toujours dans cet ordre :

1. new-run.sh crée une copie isolée de l'application dans ~/shoplite-runs/.
2. run-agent.sh lance l'agent (par exemple dev-backend) sur cette copie. C'est la seule étape qui appelle Claude et qui coûte des tokens.
3. check-run.sh vérifie le travail de l'agent : gate, tests cachés, contrôles propres à la tâche.
4. score.py donne la note et le verdict.

### Étape 0 : avant chaque session

Dans Git Bash :

cd /c/Dev/claude-code/shoplite-agent-eval
export PATH="$HOME/.dotnet:$PATH"

Arrête aussi tout dotnet run ou npm run dev qui tourne encore : les runs utilisent les ports 5080 et 5173.

### Étape 1 : tester un agent sur une tâche

Commence par une seule tâche, BE-02 par exemple :

RUN=$(bash scripts/new-run.sh BE-02 1)        # 1 = numéro du run
bash scripts/run-agent.sh "$RUN" --dry-run     # facultatif : affiche la commande claude sans la lancer
bash scripts/run-agent.sh "$RUN"               # l'agent travaille (quelques minutes)
bash scripts/check-run.sh "$RUN"               # correction automatique
python scripts/score.py BE-02 --runs 1         # note + verdict

Le résultat détaillé se trouve dans $RUN/.eval/result.json.

Pour refaire un run existant, ajoute --force : bash scripts/new-run.sh BE-02 1 --force.

### Étape 2 : tester un agent précis

Choisis les tâches de l'agent qui t'intéresse :

┌────────────────────────────────────────────┬─────────────────────────────────────────────────────────┐
│                   Agent                    │                         Tâches                          │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ dev-backend                                │ BE-01 à BE-06, ADV-02                                   │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ dev-frontend                               │ FE-01 à FE-05, ADV-01                                   │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ code-reviewer                              │ CR-01, CR-02                                            │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ security-reviewer                          │ SR-01, SR-02                                            │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ analyst                                    │ AN-01, AN-02                                            │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ dev-integrator                             │ DI-01, DI-02                                            │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ story-validator                            │ SV-01, SV-02                                            │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ product-owner                              │ PO-01, PO-02                                            │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ product-manager                            │ PM-01, PM-02 (longues : environ 90 min et 25 $ chacune) │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ conventions-scout, unit-tester, doc-writer │ CS-01, UT-01, DW-01                                     │
└────────────────────────────────────────────┴─────────────────────────────────────────────────────────┘

Par exemple, pour tout code-reviewer :

for task in CR-01 CR-02; do
  RUN=$(bash scripts/new-run.sh "$task" 1 --force)
  bash scripts/run-agent.sh "$RUN" || echo "agent exit $? on $task"
  bash scripts/check-run.sh "$RUN"
done
python scripts/score.py CR-01 --runs 1
python scripts/score.py CR-02 --runs 1

### Étape 3 : campagne complète (les 30 tâches × 3 runs)

for task in $(ls tasks | grep -v '^_'); do
  for n in 1 2 3; do
    RUN=$(bash scripts/new-run.sh "$task" "$n" --force)
    bash scripts/run-agent.sh "$RUN" || echo "agent exit $? on $task run $n"
    bash scripts/check-run.sh "$RUN"
  done
done
python scripts/score.py --all --update-sheet --json campaign.score.json

⚠️ Ça fait 90 runs d'agent, donc plusieurs heures et un coût important (PM-01 et PM-02 seules, c'est environ 150 $ pour 3 runs chacune). Lance les tâches une après l'autre, jamais en parallèle (conflit de ports). Pour une première fois, je te conseille plutôt l'étape 1 ou 2.

--update-sheet remplit la fiche docs/evaluation-sheet.md.

### À savoir

- Note manuelle (qualité du code, etc.) : crée $RUN/.eval/manual-scores.json, par exemple {"code_quality": 2, "notes": "…"}, puis relance score.py.
- Ta config personnelle influence les résultats : claude -p charge ton ~/.claude/CLAUDE.md, tes skills et tes plugins. Pour comparer deux campagnes, garde la même configuration.
- Si tu modifies un agent dans web-team-agents, relance bash ../web-team-agents/install.sh pour le recopier dans ~/.claude/agents/ avant de refaire des runs.
- La description de chaque tâche (ce qui est attendu, les critères de réussite) se trouve dans tasks/<ID>/task.md, et la notation dans docs/scoring-criteria.md.
