Tu es un architecte logiciel senior, développeur full-stack expert en C#/.NET, React/TypeScript, SignalR, SQLite, Phaser 3 et interfaces pixel art.

Crée un projet complet et exécutable nommé `claude-pixel-office`.

## Objectif

Construis un bureau virtuel pixel art geek cyberpunk qui permet de visualiser en temps réel le travail de l'équipe d'agents `web-team-agents` (path: `C:\Dev\claude-code\web-team-agents`)

L’application doit donner l’impression d’observer un vrai bureau technologique futuriste : chaque agent est un personnage pixel art à son poste, avec une animation qui reflète précisément son activité actuelle.

Le projet doit fonctionner localement, sans dépendance à des services payants. Il doit être utilisable avec Claude Code via des hooks qui enregistrent les événements du cycle de vie des agents et des outils.

## Équipe d’agents

Utilise exactement ces identifiants d’agents, sans les renommer :

- product-owner
- product-manager
- analyst
- conventions-scout
- dev-backend
- dev-frontend
- dev-integrator
- code-reviewer
- unit-tester
- security-reviewer
- story-validator
- doc-writer

## Stack obligatoire

### Frontend

- React 19
- TypeScript en mode strict
- Vite
- Phaser 3 pour le rendu de la scène pixel art
- CSS moderne ou CSS Modules
- Client SignalR officiel
- Aucun framework UI lourd
- Tests avec Vitest et React Testing Library

### Backend

- .NET 10 / ASP.NET Core
- C#
- SignalR
- SQLite avec Entity Framework Core
- API REST documentée avec OpenAPI
- Tests xUnit
- Architecture propre et pragmatique :
  - `Domain`
  - `Application`
  - `Infrastructure`
  - `Api`

### Outils

- Docker Compose facultatif mais recommandé
- Scripts de lancement Windows PowerShell, macOS/Linux Bash
- ESLint + Prettier côté frontend
- `dotnet format` côté backend

## Expérience visuelle

Crée une scène 2D en pixel art vue légèrement de haut, dans un bureau cyberpunk nocturne.

Le bureau contient les zones suivantes :

1. Zone Produit
   - product-owner
   - product-manager
   - analyst
   - conventions-scout
   - Décor : tableaux Kanban holographiques, post-its lumineux, mur de feuilles de route, écrans de priorisation.

2. Zone Développement
   - dev-backend
   - dev-frontend
   - dev-integrator
   - Décor : écrans de code, serveurs, câbles, consoles, moniteurs multi-écrans.

3. Zone Qualité
   - code-reviewer
   - unit-tester
   - security-reviewer
   - story-validator
   - Décor : laboratoire de tests, écran de CI, scanner de vulnérabilités, éprouvettes numériques, alertes contrôlées.

4. Zone Documentation
   - doc-writer
   - Décor : terminal de documentation, imprimante futuriste, bibliothèque technique et écrans avec diagrammes.

5. Poste central
   - Un mur de commandement global avec :
     - agents actifs / inactifs
     - nombre de tâches en cours
     - succès et erreurs récentes
     - durée de session
     - activité Git simulée ou réelle si disponible
     - flux d’événements récent

## Palette et style

Utilise un style pixel art net, lisible, élégant et cyberpunk geek, sans personnages ou logos protégés.

Palette principale :

- Fond sombre : #10101B
- Gris inactif : #3A3A46
- Rose foncé : #C2185B
- Rose actif : #FF69B4
- Bleu clair : #87CEEB
- Or pour succès/livrables : #FFD700
- Vert terminal : #43D17A
- Rouge erreur : #EF5350
- Violet accent : #9C6ADE

Ajoute :

- fenêtres avec pluie nocturne et skyline futuriste fictif
- enseignes néon abstraites
- écrans CRT
- halos lumineux discrets
- micro-effets de glitch seulement en cas d’erreur
- léger mouvement d’ambiance : ventilation, scintillement, particules, écrans animés

La lisibilité des données doit toujours être prioritaire sur les effets décoratifs.

## États et animations des agents

Chaque agent doit avoir :

- un bureau et un sprite pixel art distinct
- une couleur d’accent propre selon son domaine
- une carte d’information affichable au clic
- son statut courant
- la tâche active
- le dernier outil utilisé
- la durée d’activité
- les derniers événements

Implémente au minimum ces états :

- `offline`
- `idle`
- `planning`
- `reading`
- `coding`
- `testing`
- `reviewing`
- `waiting`
- `success`
- `error`

Mappe les événements Claude Code à une animation :

| Événement ou outil | État visuel |
|---|---|
| SubagentStart | planning |
| Read, Grep, Glob | reading |
| Edit, Write | coding |
| Bash avec test/build/lint | testing |
| Bash autre | coding |
| WebSearch, WebFetch | reading |
| SubagentStop avec succès | success |
| PostToolUseFailure ou StopFailure | error |
| aucune activité pendant 20 secondes | idle |

Animations attendues :

- idle : assis, écran peu lumineux, animation lente
- planning : observe des documents ou un tableau holographique
- reading : scanner bleu ou lignes de texte qui défilent
- coding : frappe au clavier, écran rose ou vert
- testing : terminal intense, jauge de tests et particules
- reviewing : loupe holographique ou comparaison de diff
- waiting : tasse de café, sablier ou petit drone
- success : écran or/vert et effet de confirmation discret
- error : écran rouge, léger glitch et icône d’alerte

## Temps réel et télémétrie

Conçois un système de télémétrie de développement local.

### Format d’événement commun

Chaque événement doit respecter ce contrat :

```json
{
  "id": "uuid",
  "timestamp": "2026-10-16T08:00:00.000-04:00",
  "sessionId": "string",
  "agentId": "dev-backend",
  "eventType": "PostToolUse",
  "toolName": "Bash",
  "status": "running",
  "taskId": "T-042",
  "summary": "Exécution des tests unitaires du backend",
  "metadata": {
    "exitCode": 0,
    "durationMs": 1200
  }
}
```

### Backend

Implémente :

- `POST /api/events` pour recevoir un événement
- `GET /api/agents` pour l’état actuel des agents
- `GET /api/events?limit=100` pour l’historique
- `GET /api/sessions` pour les sessions récentes
- un hub SignalR nommé `/hubs/office`
- diffusion instantanée des événements et états agent mis à jour
- stockage SQLite de l’historique
- agrégation d’état en mémoire ou en base
- validation stricte des entrées
- gestion d’erreurs et logs structurés

Ne stocke jamais :
- prompts complets
- sorties terminal complètes
- secrets
- tokens API
- contenu de fichiers source

Conserve seulement des résumés sûrs, le nom d’outil, le statut, les dates et des métadonnées minimales.

### Simulateur

Comme les hooks réels ne sont pas toujours actifs durant le développement, fournis un simulateur intégré.

Le simulateur doit :

- générer un flux réaliste d’événements pour les 12 agents
- permettre de démarrer, mettre en pause, accélérer et réinitialiser la simulation
- déclencher des scénarios : développement normal, tests en échec, revue de code, faille de sécurité, documentation terminée
- permettre de sélectionner manuellement l’état d’un agent
- être clairement étiqueté `Simulation locale`

## Intégration Claude Code

Ajoute un dossier `.claude/` contenant :

- `.claude/settings.example.json`
- `.claude/hooks/office-event-hook.sh`
- `.claude/hooks/office-event-hook.ps1`
- `.claude/README.md`

Les scripts de hook doivent :

1. Lire l’entrée JSON reçue depuis Claude Code.
2. Extraire uniquement les champs non sensibles.
3. Déterminer l’agent concerné si disponible.
4. Convertir l’événement vers le contrat commun.
5. Envoyer l’événement au backend local à `http://localhost:5200/api/events`.
6. Ne jamais faire échouer Claude Code si le bureau virtuel est arrêté.
7. Produire un log local minimal et sûr si la requête HTTP échoue.

Dans `.claude/settings.example.json`, donne des exemples commentés de hooks pour :

- `SessionStart`
- `SubagentStart`
- `PreToolUse`
- `PostToolUse`
- `PostToolUseFailure`
- `SubagentStop`
- `Stop`
- `StopFailure`

Utilise les matchers appropriés pour les outils, notamment `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `WebSearch` et `WebFetch`.

Explique que le nom des champs exacts peut varier selon la version de Claude Code; le parseur de hook doit donc être défensif, journaliser les schémas inconnus et éviter de briser le workflow.

## Interface utilisateur

Construis une interface avec :

- la scène pixel art centrale comme vue principale
- un panneau latéral repliable avec la liste des 12 agents
- une recherche par agent
- filtres par zone et par statut
- une fiche agent au clic :
  - nom
  - rôle lisible
  - statut
  - tâche
  - outil courant
  - durée
  - 10 derniers événements
- un panneau inférieur de flux d’activité
- un bouton de mode `Simulation locale`
- un bouton `Vue Live`
- un bouton `Rejouer une session`
- une timeline simple permettant de parcourir l’historique
- indicateur SignalR connecté / déconnecté
- design réactif, mais l’expérience optimale doit être en écran large

Ajoute un mode accessibilité :

- réduction des animations
- contraste renforcé
- alternatives textuelles pour les animations et couleurs
- navigation clavier pour ouvrir les cartes des agents

## Modèle de rôles affichés

Utilise ces intitulés à l’interface :

- product-owner : Product Owner
- product-manager : Product Manager
- analyst : Analyste
- conventions-scout : Éclaireur de conventions
- dev-backend : Développeur backend
- dev-frontend : Développeur frontend
- dev-integrator : Intégrateur frontend-backend
- code-reviewer : Réviseur de code
- unit-tester : Testeur unitaire
- security-reviewer : Réviseur sécurité
- story-validator : Validateur de story
- doc-writer : Rédacteur technique

## Qualité obligatoire

- TypeScript strict, sans `any` injustifié.
- C# avec nullable reference types activé.
- DTOs séparés des entités de persistance.
- Pas de données sensibles dans les événements, logs ou UI.
- Gestion explicite des états de connexion SignalR.
- États vides et erreurs visuellement soignés.
- Tests :
  - backend : API d’ingestion, validation, agrégation d’état et hub
  - frontend : composants de panneau, mapping des états, client SignalR
- Données de démonstration complètes.
- README clair en français.
- Commentaires uniquement lorsqu’ils expliquent une décision technique non évidente.

## Livrables attendus

Génère l’intégralité des fichiers nécessaires, avec leur chemin et leur contenu.

Inclure au minimum :

```text
claude-pixel-office/
  README.md
  docker-compose.yml
  .gitignore
  .claude/
    README.md
    settings.example.json
    hooks/
      office-event-hook.sh
      office-event-hook.ps1
  backend/
    ClaudePixelOffice.sln
    src/
    tests/
  frontend/
    package.json
    vite.config.ts
    src/
    public/
  docs/
    architecture.md
    event-contract.md
    claude-code-hooks.md
    screenshots.md
```

Pour les visuels pixel art, ne télécharge aucune ressource protégée. Crée des sprites originaux très simples avec :
- formes dessinées dans Phaser,
- atlas générés localement,
- ou fichiers SVG/PNG originaux créés dans le projet.

## Réponse attendue

Travaille en phases, mais produis un résultat immédiatement exploitable :

1. Montre d’abord l’arborescence complète.
2. Génère ensuite tous les fichiers essentiels, sans pseudo-code.
3. Priorise un MVP fonctionnel de bout en bout :
   - simulateur -> API -> SignalR -> scène Phaser -> panneau React.
4. Ajoute ensuite les scripts de hooks Claude Code.
5. Termine par les commandes exactes pour :
   - lancer le backend
   - lancer le frontend
   - lancer la simulation
   - configurer les hooks
   - exécuter les tests
6. Si une dépendance, une API ou un schéma Claude Code est incertain, isole cette partie derrière une interface, documente l’hypothèse et fournis un fallback fonctionnel.

Ne me donne pas seulement une maquette ou une explication : crée le code complet d’un prototype local fonctionnel.