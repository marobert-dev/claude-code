# Fiche d'évaluation

Une fiche par agent et par tâche (copier le modèle §1 dans un fichier par campagne, ou le remplir ici), et un tableau
récapitulatif (§2) que `python scripts/score.py --all --update-sheet` remplit automatiquement à partir des
`result.json` (une ligne par tâche × run ; les lignes sans résultat restent vides).

## 1. Modèle de fiche (agent × tâche)

| Rubrique | Valeur |
|---|---|
| Agent | `<nom>` |
| Modèle (frontmatter) / modèle réellement utilisé | `<sonnet/opus/haiku>` / `<metrics.model_usage>` |
| SHA de `web-team-agents` | `<result.agents_sha>` (hash du fichier agent : `<metrics.agent_file_sha256>`) |
| Version de Claude Code | `<result.claude_version>` |
| SHA du kit | `<result.kit_sha>` |
| ID de tâche | `<TASK-ID>` |
| Date | `<result.checked_at>` |
| Répertoire de run | `<result.run_dir>` |
| Prompt utilisé | `tasks/<TASK-ID>/prompt.txt` (copier le texte) |
| Mode d'invocation | `<task.json invocation>` |
| Nombre de runs | `<3>` |

### Résultat par run

| Run | Gate | Tests visibles | Tests cachés (passés/total) | Fichiers modifiés | Lignes +/− | Hors périmètre | Marqueurs TODO/REVIEW/SECURITY ajoutés | Entrées `.decisions/` | `Memory:` | Tours | Coût $ | Durée s | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | | | | | |
| 2 | | | | | | | | | | | | | |
| 3 | | | | | | | | | | | | | |

### Sécurité, accessibilité, i18n

| Rubrique | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Failles introduites | | | |
| Failles corrigées | | | |
| Problèmes d'accessibilité | | | |
| Problèmes i18n FR/EN | | | |

### Score par critère (0/1/2, « n/a » si non applicable)

| Critère | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Gate et tests | | | |
| Correction fonctionnelle | | | |
| Respect du périmètre | | | |
| Respect du rôle et du protocole | | | |
| Contrat API | | | |
| Sécurité | | | |
| Qualité du code | | | |
| Qualité des tests produits | | | |
| Précision de revue | | | |
| Accessibilité et i18n FR/EN | | | |
| Performance | | | |
| Efficacité | | | |
| **Score total %** | | | |
| **Verdict du run** | | | |
| Stabilité (tâche) | | | |
| **Verdict de la tâche** | | | |

### Observations

- …

### Actions d'amélioration proposées pour le fichier de l'agent

Citer la section concernée du `.md` de l'agent (`web-team-agents/agents/<agent>.md`) et la modification proposée :

| Section de l'agent | Constat (run, preuve) | Modification proposée |
|---|---|---|
| ex. `dev-backend.md` › « Implementation » point 4 | run 2 : endpoint ouvert par omission (`check be03-customer`) | ajouter « vérifier chaque `[Authorize]` contre le rôle exigé par le contrat » |

## 2. Tableau récapitulatif (rempli par `score.py --update-sheet`)

Colonnes : Gate = vert/rouge en fin de run ; Hidden = tests cachés passés/total ; TODO/REVIEW/SECURITY = marqueurs
ajoutés ; .decisions = nouvelles entrées ; Memory = ligne de fin de rapport.

<!-- score:begin -->
| Task | Agent | Run | Gate | Hidden | Score % | Verdict | Blocking | Turns | Cost $ | Duration s | Files | +/- | Out of scope | TODO/REVIEW/SECURITY | .decisions | Memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ADV-01 | dev-frontend | 1 | | | | | | | | | | | | | | |
| ADV-01 | dev-frontend | 2 | | | | | | | | | | | | | | |
| ADV-01 | dev-frontend | 3 | | | | | | | | | | | | | | |
| ADV-02 | dev-backend | 1 | | | | | | | | | | | | | | |
| ADV-02 | dev-backend | 2 | | | | | | | | | | | | | | |
| ADV-02 | dev-backend | 3 | | | | | | | | | | | | | | |
| AN-01 | analyst | 1 | | | | | | | | | | | | | | |
| AN-01 | analyst | 2 | | | | | | | | | | | | | | |
| AN-01 | analyst | 3 | | | | | | | | | | | | | | |
| AN-02 | analyst | 1 | | | | | | | | | | | | | | |
| AN-02 | analyst | 2 | | | | | | | | | | | | | | |
| AN-02 | analyst | 3 | | | | | | | | | | | | | | |
| BE-01 | dev-backend | 1 | | | | | | | | | | | | | | |
| BE-01 | dev-backend | 2 | | | | | | | | | | | | | | |
| BE-01 | dev-backend | 3 | | | | | | | | | | | | | | |
| BE-02 | dev-backend | 1 | | | | | | | | | | | | | | |
| BE-02 | dev-backend | 2 | | | | | | | | | | | | | | |
| BE-02 | dev-backend | 3 | | | | | | | | | | | | | | |
| BE-03 | dev-backend | 1 | | | | | | | | | | | | | | |
| BE-03 | dev-backend | 2 | | | | | | | | | | | | | | |
| BE-03 | dev-backend | 3 | | | | | | | | | | | | | | |
| BE-04 | dev-backend | 1 | | | | | | | | | | | | | | |
| BE-04 | dev-backend | 2 | | | | | | | | | | | | | | |
| BE-04 | dev-backend | 3 | | | | | | | | | | | | | | |
| BE-05 | dev-backend | 1 | | | | | | | | | | | | | | |
| BE-05 | dev-backend | 2 | | | | | | | | | | | | | | |
| BE-05 | dev-backend | 3 | | | | | | | | | | | | | | |
| BE-06 | dev-backend | 1 | | | | | | | | | | | | | | |
| BE-06 | dev-backend | 2 | | | | | | | | | | | | | | |
| BE-06 | dev-backend | 3 | | | | | | | | | | | | | | |
| CR-01 | code-reviewer | 1 | | | | | | | | | | | | | | |
| CR-01 | code-reviewer | 2 | | | | | | | | | | | | | | |
| CR-01 | code-reviewer | 3 | | | | | | | | | | | | | | |
| CR-02 | code-reviewer | 1 | | | | | | | | | | | | | | |
| CR-02 | code-reviewer | 2 | | | | | | | | | | | | | | |
| CR-02 | code-reviewer | 3 | | | | | | | | | | | | | | |
| CS-01 | conventions-scout | 1 | | | | | | | | | | | | | | |
| CS-01 | conventions-scout | 2 | | | | | | | | | | | | | | |
| CS-01 | conventions-scout | 3 | | | | | | | | | | | | | | |
| DI-01 | dev-integrator | 1 | | | | | | | | | | | | | | |
| DI-01 | dev-integrator | 2 | | | | | | | | | | | | | | |
| DI-01 | dev-integrator | 3 | | | | | | | | | | | | | | |
| DI-02 | dev-integrator | 1 | | | | | | | | | | | | | | |
| DI-02 | dev-integrator | 2 | | | | | | | | | | | | | | |
| DI-02 | dev-integrator | 3 | | | | | | | | | | | | | | |
| DW-01 | doc-writer | 1 | | | | | | | | | | | | | | |
| DW-01 | doc-writer | 2 | | | | | | | | | | | | | | |
| DW-01 | doc-writer | 3 | | | | | | | | | | | | | | |
| FE-01 | dev-frontend | 1 | | | | | | | | | | | | | | |
| FE-01 | dev-frontend | 2 | | | | | | | | | | | | | | |
| FE-01 | dev-frontend | 3 | | | | | | | | | | | | | | |
| FE-02 | dev-frontend | 1 | | | | | | | | | | | | | | |
| FE-02 | dev-frontend | 2 | | | | | | | | | | | | | | |
| FE-02 | dev-frontend | 3 | | | | | | | | | | | | | | |
| FE-03 | dev-frontend | 1 | | | | | | | | | | | | | | |
| FE-03 | dev-frontend | 2 | | | | | | | | | | | | | | |
| FE-03 | dev-frontend | 3 | | | | | | | | | | | | | | |
| FE-04 | dev-frontend | 1 | | | | | | | | | | | | | | |
| FE-04 | dev-frontend | 2 | | | | | | | | | | | | | | |
| FE-04 | dev-frontend | 3 | | | | | | | | | | | | | | |
| FE-05 | dev-frontend | 1 | | | | | | | | | | | | | | |
| FE-05 | dev-frontend | 2 | | | | | | | | | | | | | | |
| FE-05 | dev-frontend | 3 | | | | | | | | | | | | | | |
| PM-01 | product-manager | 1 | | | | | | | | | | | | | | |
| PM-01 | product-manager | 2 | | | | | | | | | | | | | | |
| PM-01 | product-manager | 3 | | | | | | | | | | | | | | |
| PM-02 | product-manager | 1 | | | | | | | | | | | | | | |
| PM-02 | product-manager | 2 | | | | | | | | | | | | | | |
| PM-02 | product-manager | 3 | | | | | | | | | | | | | | |
| PO-01 | product-owner | 1 | | | | | | | | | | | | | | |
| PO-01 | product-owner | 2 | | | | | | | | | | | | | | |
| PO-01 | product-owner | 3 | | | | | | | | | | | | | | |
| PO-02 | product-owner | 1 | | | | | | | | | | | | | | |
| PO-02 | product-owner | 2 | | | | | | | | | | | | | | |
| PO-02 | product-owner | 3 | | | | | | | | | | | | | | |
| SR-01 | security-reviewer | 1 | | | | | | | | | | | | | | |
| SR-01 | security-reviewer | 2 | | | | | | | | | | | | | | |
| SR-01 | security-reviewer | 3 | | | | | | | | | | | | | | |
| SR-02 | security-reviewer | 1 | | | | | | | | | | | | | | |
| SR-02 | security-reviewer | 2 | | | | | | | | | | | | | | |
| SR-02 | security-reviewer | 3 | | | | | | | | | | | | | | |
| SV-01 | story-validator | 1 | | | | | | | | | | | | | | |
| SV-01 | story-validator | 2 | | | | | | | | | | | | | | |
| SV-01 | story-validator | 3 | | | | | | | | | | | | | | |
| SV-02 | story-validator | 1 | | | | | | | | | | | | | | |
| SV-02 | story-validator | 2 | | | | | | | | | | | | | | |
| SV-02 | story-validator | 3 | | | | | | | | | | | | | | |
| UT-01 | unit-tester | 1 | | | | | | | | | | | | | | |
| UT-01 | unit-tester | 2 | | | | | | | | | | | | | | |
| UT-01 | unit-tester | 3 | | | | | | | | | | | | | | |
<!-- score:end -->

### Verdicts par tâche

<!-- verdicts:begin -->
| Task | Agent | Mean score % | Stability | Task verdict |
|---|---|---|---|---|
| ADV-01 | dev-frontend | | | |
| ADV-02 | dev-backend | | | |
| AN-01 | analyst | | | |
| AN-02 | analyst | | | |
| BE-01 | dev-backend | | | |
| BE-02 | dev-backend | | | |
| BE-03 | dev-backend | | | |
| BE-04 | dev-backend | | | |
| BE-05 | dev-backend | | | |
| BE-06 | dev-backend | | | |
| CR-01 | code-reviewer | | | |
| CR-02 | code-reviewer | | | |
| CS-01 | conventions-scout | | | |
| DI-01 | dev-integrator | | | |
| DI-02 | dev-integrator | | | |
| DW-01 | doc-writer | | | |
| FE-01 | dev-frontend | | | |
| FE-02 | dev-frontend | | | |
| FE-03 | dev-frontend | | | |
| FE-04 | dev-frontend | | | |
| FE-05 | dev-frontend | | | |
| PM-01 | product-manager | | | |
| PM-02 | product-manager | | | |
| PO-01 | product-owner | | | |
| PO-02 | product-owner | | | |
| SR-01 | security-reviewer | | | |
| SR-02 | security-reviewer | | | |
| SV-01 | story-validator | | | |
| SV-02 | story-validator | | | |
| UT-01 | unit-tester | | | |
<!-- verdicts:end -->
