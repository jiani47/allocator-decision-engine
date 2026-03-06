# Equi Frontend

React 19 + TypeScript single-page app implementing a 4-step investment analysis wizard.

## Stack

- **React 19** + TypeScript (strict mode)
- **Vite 7** — dev server with HMR, proxies `/api` to backend on `:8000`
- **shadcn/ui** (Radix) — headless UI primitives
- **Tailwind CSS 4** — utility-first styling
- **react-markdown** + remark-gfm — memo rendering
- **xlsx** — Excel export
- **openapi-typescript** — API type generation from FastAPI spec

## Dev Setup

```bash
npm install
npm run dev           # Vite dev server on http://localhost:5173
npm run codegen       # Regenerate API types from running backend
npm run build         # Production build → dist/
```

The backend must be running on `:8000` for API calls. Vite proxies `/api` requests automatically.

## Architecture

### State Management
`src/context/WizardContext.tsx` — Central React context managing all cross-step state (mandate, upload results, benchmark, rankings, memo). TypeScript types mirror Python Pydantic models from `app/core/schemas.py`.

### Wizard Steps (`src/steps/`)
| Step | Component | Description |
|------|-----------|-------------|
| 1 | `MandateForm` | Configure constraints, weights, strategy filters |
| 2 | `UploadReview` | Upload CSV, review LLM extraction, resolve warnings |
| 3 | `RankingView` | Benchmark selection, rankings, optional re-rank |
| 4 | `MemoExport` | Stream memo, citation badges, Excel/PDF export |

### Hooks (`src/hooks/`)
One hook per API endpoint — hooks own all fetch logic and loading/error state:
- `useUpload` — multipart file upload
- `useBenchmark` — benchmark data fetch
- `useRank` — fund ranking
- `useRerank` — LLM re-ranking
- `useMemoStream` — SSE streaming with text accumulation

### Key Components (`src/components/`)
- `CitationBadge` — Inline claim annotation with evidence popover
- `ClaimsPanel` — Claims list with metric references
- `CalcSheet` — Metric calculation detail view
- `AppSidebar` + `StepIndicator` — Navigation

## Conventions

- Hooks own API logic — components never call fetch directly
- Types use `snake_case` (matching Python JSON serialization)
- shadcn/ui for all UI primitives — no custom component library
- Tailwind utility classes — no CSS modules
