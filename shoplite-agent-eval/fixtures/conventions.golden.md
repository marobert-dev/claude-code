# Project conventions (auto-generated — read by all agents)

## Project rules
not present (no CLAUDE.md or AGENTS.md in the workspace)

## Repositories
- `.` (workspace root, single git repo): Playwright e2e runner (`package.json`, `playwright.config.ts`, `tests/e2e/`), API contract `contracts/openapi.yaml`, gate `.claude/hooks/gate.sh` (+ `.claude/gate.local.sh`).
- `backend/` — C# / ASP.NET Core Web API on .NET 10 (`ShopLite.sln`: `src/ShopLite.Api`, `tests/ShopLite.Api.Tests`).
- `frontend/` — TypeScript / React 19 SPA built with Vite.

## Backend
- Framework / ORM / layering: ASP.NET Core controllers (`[ApiController]`, attribute routes under `/api/...`) → services (`Services/*Service.cs`, registered scoped in `Program.cs`) → EF Core `ShopLiteDbContext` (InMemory provider, no repository layer). DTOs in `Dtos/` (records for responses, classes with DataAnnotations for requests), entities in `Domain/`, never returned directly.
- Error-handling & logging pattern: services throw `AppException` subclasses (`NotFoundException` 404, `BusinessRuleException` 400, `InvalidCredentialsException` 401) from `Errors/`; `ProblemDetailsExceptionHandler` (IExceptionHandler) turns them into RFC 9457 problem details with localized title/detail; `UseStatusCodePages` gives 401/403 bodies; `ILogger<T>` with structured templates.
- Input validation approach: DataAnnotations on request DTOs + `[ApiController]` automatic 400; `ValidationProblemFactory` returns `ValidationProblemDetails` with a localized title; `ErrorMessage` values are resource keys (`Validation.Range`, `Validation.Required`, `Validation.StringLength`).
- AuthN/AuthZ mechanism: JWT bearer (`Auth/AuthenticationSetup.cs`, `TokenService`), claims `sub` (user id, read with `User.GetUserId()`), `name`, `role`; `[Authorize]` / `[Authorize(Roles = Roles.Admin)]` on controllers/actions; roles `customer`, `admin`.
- Config / secrets mechanism: `appsettings*.json` + environment variables; JWT signing key from `SHOPLITE_JWT_KEY` (dev value only in `appsettings.Development.json`), bound in `JwtSettings` with `ValidateOnStart`.
- Migrations tool: not present (EF Core InMemory, `EnsureCreated` + `Data/DataSeeder.cs` seed at startup; users alice/bob customers, admin admin).
- Push-notification integration (if any): not present.

## Frontend (web)
- Framework / language (TS or JS): React 19 + TypeScript (strict), Vite 6, function components and hooks.
- State management: local `useState`/`useCallback`; auth session in React context (`auth/AuthContext.ts` + `auth/AuthProvider.tsx`, token in `sessionStorage` key `shoplite.auth`); `LoadState<T>` union (`loading | error | success`) in `utils/loadState.ts`.
- Styling approach: one global stylesheet `src/styles.css` with CSS custom properties and BEM-like class names.
- Routing: React Router 7 (`BrowserRouter` in `main.tsx`, routes in `App.tsx` `AppRoutes`, `RequireAuth` wrapper with optional `role`).
- Folder structure & naming: `src/api/` (one module per resource, `apiRequest` in `client.ts`, hand-written types in `types.ts`), `src/pages/*Page.tsx`, `src/components/` (PascalCase files, named exports), `src/utils/`; UI states via `LoadingState` / `EmptyState` / `ErrorState` (`components/StatusMessage.tsx`).

## Mobile (React Native)
- Navigation / styling / state: not present
- Offline/caching approach: not present
- Push / deep-link libraries: not present

## i18n
- Mechanism, locale file locations, key naming (FR + EN): web — i18next + react-i18next, `frontend/src/i18n/index.ts`, `frontend/src/i18n/locales/{en,fr}.json`, nested camelCase keys by screen (`cart.total`, `orders.empty`), plurals with `_one`/`_other`, language stored in `localStorage` `shoplite.lang`, sent as `Accept-Language`. API — `IStringLocalizer<SharedResource>` with `backend/src/ShopLite.Api/Resources/SharedResource.resx` (en) and `SharedResource.fr.resx`, dotted keys (`Error.ProductNotFound`), culture from `Accept-Language` (en default, fr).

## API contract
- Location of `contracts/openapi.yaml` (or `not present`): `contracts/openapi.yaml` (OpenAPI 3.1, operationIds in camelCase, bearerAuth security scheme, problem+json errors).
- Client-generation tool in use (or `not present`): not present (types hand-written in `frontend/src/api/types.ts`).
- Spec-emitting tool on the backend (or `not present`): Microsoft.AspNetCore.OpenApi — `GET /openapi/v1.json` in Development.

## Tests
- Unit framework(s) and how tests are laid out: backend xUnit + `WebApplicationFactory<Program>` integration tests in `backend/tests/ShopLite.Api.Tests` (`Infrastructure/ShopLiteApiFactory.cs` gives each factory its own InMemory database; helpers `CreateAuthenticatedClientAsync`, `TestUsers`); frontend Vitest + React Testing Library + user-event + jest-axe in `frontend/tests/*.test.tsx` (`tests/testUtils.tsx`: `renderApp`, `mockFetch`, `signInAs`).
- E2E framework(s) (Playwright / Maestro / Detox / other / not present): Playwright (Chromium).
- Accessibility test helpers: jest-axe in frontend unit tests; @axe-core/playwright not present.
- Where e2e tests live: `tests/e2e/<story-id>/` at the workspace root (`tests/e2e/smoke/` exists); titles start with `[<story-id>]`; parametrized by locale (`en`, `fr` via `localStorage` `shoplite.lang`). `playwright.config.ts` reads `SHOPLITE_API_PORT` (default 5080) and `SHOPLITE_WEB_PORT` (default 5173) to move both servers when a port is taken.

## Commands
Exact commands, run from the stated directory. Write `not present` if a step doesn't exist.

| Step | Directory | Command |
|---|---|---|
| lint | `frontend/` | `npm run lint` |
| typecheck | `frontend/` | `npm run typecheck` |
| build | `frontend/` and `backend/` | `npm run build` ; `dotnet build ShopLite.sln` |
| unit test | `frontend/` and `backend/` | `npm test` ; `dotnet test ShopLite.sln` |
| e2e test | root | `npx playwright test` |
| e2e test by tag/grep | root | `npx playwright test --grep "\[<story-id>\]"` |
| start app (for e2e) | root | started by `playwright.config.ts` `webServer` (`dotnet run --project backend/src/ShopLite.Api --no-launch-profile --urls http://localhost:5080` and `npm --prefix frontend run dev`, port 5173) |

Full gate: `bash .claude/hooks/gate.sh` from the root (delegates to `.claude/gate.local.sh`).

## Security tooling present
gitleaks / semgrep / osv-scanner / npm audit / dotnet list package / secret-scan.sh: npm audit (npm 12), `dotnet list package --vulnerable` (.NET 10 SDK) and `.claude/hooks/secret-scan.sh`; gitleaks, semgrep, osv-scanner, schemathesis and oasdiff not installed.

## Developer tooling present
none (no language server or contract linter installed)

## Change log
- 2026-10-14 bootstrap (golden reference written for the evaluation kit)
