# AGENTS.md — PreFlight WebUI

> READ THIS FILE FIRST before working on the WebUI.
> Updated 2026-07-09.

## Current Phase: Frontend-Backend Integration

The webUI is fully built with mock data. We are now connecting it to the real backend.
Backend is complete (90/90 tests, 5 endpoints). Types already match. Only `lib/api.ts` changes.

**Read `reports/preflight-status-report.md` first** for full context on what exists vs what's fabricated.

## Critical Rules

1. **Minimal surgical changes** — swap mock for real fetch, remove fabricated fields. No redesigns, no refactors.
2. **Additive approach** — don't break existing features. New capabilities go alongside existing ones.
3. **API signatures are contracts.** Functions in `lib/api.ts` define the interface. Signatures and return types stay stable.
4. **Types are sacred.** `lib/types.ts` mirrors backend Pydantic models. Never change field names without explicit instruction.
5. **Dark theme only.** No light theme.
6. **No external UI kits.** Use custom components in `components/ui/`.
7. **Recharts for charts.** Don't swap chart libraries.
8. **Responsive required.** Works at 320px, 768px, 1024px, 1440px.
9. **Do not change page routes.** 7 routes are fixed.
10. **No `any` type.** Use `unknown` if needed, then narrow.

## File Map

| Path | What | When to read |
|------|------|-------------|
| AGENTS.md (this file) | Rules, phase, backend context | Always first |
| `../reports/preflight-status-report.md` | Full status: features, gaps, next steps | Before any work |
| `../frontend/INTEGRATION.md` | CORS setup, mock→real swap guide, endpoint status | When connecting |
| app/ | Next.js pages | When editing a page |
| lib/api.ts | API client (mock → real) | When swapping mock for fetch |
| lib/types.ts | TypeScript types (aligned with backend) | When checking data shapes |
| lib/mock-data.ts | Mock data constants | When updating mock responses |
| lib/utils.ts | Formatting helpers | When formatting numbers/dates |
| app/globals.css | CSS variables, Tailwind config | When changing design tokens |
| components/ | UI components | When editing components |

## Backend Context

Backend lives in `../repo/`. All endpoints verified working (2026-07-09).

### Endpoints That Exist (ready to connect)

| Frontend Function | Backend Endpoint | Notes |
|------------------|------------------|-------|
| `getHealth()` | `GET /api/v1/health` | Direct match |
| `analyzeDataset(input)` | `POST /api/v1/dataset/analyze` | Backend takes `{path}` for folder scan. Manual entry mode needs backend support. |
| `recommendGPU(req)` | `POST /api/v1/gpu/recommend` | Types match. Benchmark throughput in scoring. |
| `predictDuration(req)` | `POST /api/v1/predict/duration` | Types match. XGBoost model. |
| `estimateCost(req)` | `POST /api/v1/cost/estimate` | Types match. Returns `gpu_hours`, cost breakdown. |
| `getTrainingHealth(jobId)` | `POST /api/v1/training/analyze` | Backend takes `{path}` to log file. |
| `getDashboardStats()` | `GET /api/v1/dashboard/stats` | **NEW** — types need update. Backend returns experiment stats, not analysis stats. |
| `listExperiments()` | `GET /api/v1/experiments` | **NEW** — types need update. Backend returns `ExperimentRecord[]` with different fields. |
| `getTrainingMetrics()` | `GET /api/v1/training/monitor` | **NEW** — types need update. Backend returns `LiveTrainingMonitor` with curve, convergence, health. |

### Endpoints That DON'T Exist (stay mock or remove)

| Frontend Function | Issue | Action |
|------------------|-------|--------|
| `analyzeTraining(req)` | No `/analyze` endpoint. Fabricated PredictionResult fields | **Remove fabricated fields.** Call `predictDuration()` + `estimateCost()` instead. |
| `getRecentActivity()` | No endpoint | Derive from experiment list or keep mock |
| `startTraining()` / `stopTraining()` | No endpoint | Keep mock |
| `getExperiment(id)` / `deleteExperiment(id)` | No single/DELETE endpoint | Use experiments list response |
| `exportAnalysis()` | No export | Keep mock |
| `listGPUs()` | No dedicated endpoint | Add `GET /api/v1/gpus` to backend, or embed |
| `listGPUBenchmarks()` | No dedicated endpoint | Add `GET /api/v1/benchmarks` to backend, or embed |
| `listCloudOfferings()` | No dedicated endpoint | Add `GET /api/v1/cloud` to backend, or embed |

### Type Updates Needed (3 mismatches)

1. **DashboardStats** — backend returns `total_experiments, running, completed, failed, avg_accuracy, best_accuracy, total_gpu_hours, convergence_rate_percent, active_experiment_id`. Frontend has `total_analyses, active_jobs, datasets_analyzed, avg_savings`.
2. **Experiment** — backend returns `ExperimentRecord` with `params_million, total_epochs, epochs_completed, final_accuracy, best_val_loss, convergence, duration_hours, started_at, target_accuracy`. Frontend has `runtime_hours, cost_usd, accuracy, date`.
3. **Training metrics** — backend returns `LiveTrainingMonitor` with `epoch_progress_percent, convergence_status, health_score, health_grade, curve: EpochPoint[], warnings, recommendations`. Frontend has separate `EpochMetrics[]` and `TrainingAnalysisResult`.

### Fabricated Fields to Remove

The `/analyze` page PLACEHOLDER section shows fields with NO backend support:
- `oom_probability`, `convergence_probability`, `expected_accuracy_min/max`
- `gpu_utilization_estimate`, `carbon_footprint_kg`, `bottlenecks`

These must be removed or clearly labeled as "Roadmap — not implemented" for the demo.
The ML Duration Prediction section above it is real and ready to connect.

## Coding Conventions

- TypeScript strict mode, functional components, named exports
- `interface` for types (not `type`, except unions)
- Tailwind utility classes inline (no styled-components, no CSS modules)
- CSS variables for colors: `var(--surface)`, `var(--border)`, etc.
- Format numbers: `formatUSD()`, `formatHours()`, `formatPercent()` in `lib/utils.ts`
- Loading: `<Spinner />` in button or card
- Error: `<Alert severity="error">` with message
- Empty: `<EmptyState>` with icon and message

## Integration Steps (from frontend/INTEGRATION.md)

1. Add CORS to backend (`repo/backend/app/main.py`)
2. Create `.env.local` in webUI with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
3. Replace 5 mock functions in `lib/api.ts` with real `fetch()` calls
4. Remove fabricated fields from `/analyze` page
5. Add GPU list endpoint to backend (or embed in response)
6. Test each page against real backend
