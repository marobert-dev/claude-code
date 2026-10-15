# ShopLite

A small online shop: product catalog with search, category filter and pagination, product pages, a per-user cart,
checkout, order history and a minimal product administration. The interface and the API messages are available in
English and French.

| Part | Stack | Folder |
|---|---|---|
| API | ASP.NET Core Web API (.NET 10), EF Core InMemory, JWT bearer auth, xUnit | `backend/` |
| Web client | React 19 + TypeScript + Vite, React Router, react-i18next, Vitest + Testing Library | `frontend/` |
| API contract | OpenAPI 3.1 | `contracts/openapi.yaml` |
| End-to-end tests | Playwright | `tests/e2e/`, `playwright.config.ts` |

## Prerequisites

- .NET 10 SDK (`dotnet --list-sdks` shows a `10.0.x` line)
- Node.js 20 or later with npm
- bash and `jq` for the quality gate (Git Bash or WSL on Windows)

## Install

```bash
npm install                              # Playwright (workspace root)
npx playwright install chromium
npm --prefix frontend install
dotnet restore backend/ShopLite.sln
```

## Run the app

```bash
# API on http://localhost:5080 — OpenAPI document at /openapi/v1.json (Development only)
dotnet run --project backend/src/ShopLite.Api

# Web client on http://localhost:5173 (proxies /api to the API)
npm --prefix frontend run dev
```

The JWT signing key is read from the `SHOPLITE_JWT_KEY` environment variable (32 characters minimum).
`appsettings.Development.json` holds a development-only value; any other environment must set the variable.

Demo accounts (seeded at startup, data is in memory and resets on restart):

| User | Password | Role |
|---|---|---|
| `alice` | `Alice123!` | customer |
| `bob` | `Bob123!` | customer |
| `admin` | `Admin123!` | admin |

## Tests and checks

| Step | Directory | Command |
|---|---|---|
| Lint | `frontend/` | `npm run lint` |
| Type check | `frontend/` | `npm run typecheck` |
| Build (web) | `frontend/` | `npm run build` |
| Unit tests (web) | `frontend/` | `npm test` |
| Build (API) | `backend/` | `dotnet build ShopLite.sln` |
| Unit and integration tests (API) | `backend/` | `dotnet test ShopLite.sln` |
| End-to-end (starts API and web client) | root | `npx playwright test` |
| End-to-end, one group | root | `npx playwright test --grep "\[smoke\]"` |
| Full quality gate | root | `bash .claude/hooks/gate.sh` |

End-to-end tests are parametrized by language (English and French). Ports can be changed with
`SHOPLITE_API_PORT` and `SHOPLITE_WEB_PORT`.
